import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.align import Align
from rich import box
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.columns import Columns
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime

class ReportManager:
    def __init__(self, args, logger):
        self.args = args
        self.logger = logger

    def caclulate_values(self, combined: pd.DataFrame):
        income = combined[combined['category'] == 'Income']['amount'].sum()
        necess = combined[combined['category'] == 'Necessity']['amount'].sum()
        necess_prop = necess/income if income != 0 else 0
        discret = combined[combined['category'] == 'Discretionary']['amount'].sum()
        discret_prop = discret/income if income != 0 else 0
        savings = combined[combined['category'] == 'Savings']['amount'].sum()
        savings_prop = savings/income if income != 0 else 0
        rem = income - (necess + discret + savings)
        rem_prop = rem/income if income != 0 else 0

        return {
                    "income": income, 
                    "necessities": [necess, necess_prop], 
                    "discretionary": [discret, discret_prop], 
                    "savings": [savings, savings_prop], 
                    "remaining": [rem, rem_prop]
                }

    def group_spending(self, combined: pd.DataFrame):
        spending = combined[combined['category'].isin(['Necessity', 'Discretionary'])]
        spending_sub_cat = (spending.groupby(['category', 'sub-category'], as_index=False)['amount']
                            .sum()
                            .sort_values(by='amount', ascending=False))

        return spending_sub_cat, spending
    
    def highest_frequency_origins(self, combined: pd.DataFrame):
        origins = combined['origin']
        origins = origins.map(lambda x: x[7:] if x.startswith("AplPay") else x)
        origins = origins.map(lambda x: x[4:] if x.startswith("TST*") else x)

        origins = origins.str.lower()

        common_origins = ["safeway", "metro", "trader joe", "dunkin", "cvs", "venmo", "target", "amazon"]

        def map_origin(x):
            for common in common_origins:
                if common in x:
                    return common 
            return x

        origins = origins.map(map_origin)
        return origins.value_counts(), origins.value_counts(normalize=True)

    def generate_cli_report(self, combined: pd.DataFrame):
        self.logger.info("Generating cli report...")
        vals = self.caclulate_values(combined)
        spending_sub_cat, _ = self.group_spending(combined)

        print("\n====================Budget Report====================")
        print(f"{'Category':<15} {'Amount ($)':<15} {'Proportion of Income'}")
        print(f"_" * len(f"{'Category':<15} {'Amount ($)':<15} {'Proportion of Income'}"))

        print(f"{'Income':<15} {vals['income']:<15} {'-':<15}")

        print(f"." * len(f"{'Category':<15} {'Amount ($)':<15} {'Proportion of Income'}"))

        print(f"{'Necessities':<15} {vals['necessities'][0]:<15.2f} {vals['necessities'][1]:<15.2f}")
        print(f"{'Discretionary':<15} {vals['discretionary'][0]:<15.2f} {vals['discretionary'][1]:<15.2f}")
        print(f"{'Savings':<15} {vals['savings'][0]:<15.2f} {vals['savings'][1]:<15.2f}")

        print(f"." * len(f"{'Category':<15} {'Amount ($)':<15} {'Proportion of Income'}"))
        print(f"{'Remaining':<15} {vals['remaining'][0]:<15.2f} {vals['remaining'][1]:<15.2f}")


        print("\n\n")

        print(f"{'Top Five Spending Categories':^40}")
        for _, row in spending_sub_cat.head().iterrows():
            cat_sub_cat_str = f"{row['category']} - {row['sub-category']}:"
            print(f"{cat_sub_cat_str:<30} ${row['amount']:<15.2f}")

        if self.args.verbose > 0:
            print(f"\n{'Top Necessity Spending':^40}")
            for _, row in spending_sub_cat[spending_sub_cat['category'] == 'Necessity'].head().iterrows():
                cat_sub_cat_str = f"{row['category']} - {row['sub-category']}:"
                print(f"{cat_sub_cat_str:<30} ${row['amount']:<15.2f}")

            print(f"\n{'Top Discretionary Spending':^40}")
            for _, row in spending_sub_cat[spending_sub_cat['category'] == 'Discretionary'].head().iterrows():
                cat_sub_cat_str = f"{row['category']} - {row['sub-category']}:"
                print(f"{cat_sub_cat_str:<30} ${row['amount']:<15.2f}")

    def fmt_money(self, x):
        money_str = ""
        if x < 0:
            money_str = f"-${-1*x:,.2f}"
        else:
            money_str = f"${x:,.2f}"
        return money_str
    
    def fmt_percent(self, x):
        return f"{x:.1%}"

    def generate_pretty_cli_report(self, combined: pd.DataFrame):
        self.logger.info("Generating pretty cli report...")

        vals = self.caclulate_values(combined)
        spending_sub_cat, _ = self.group_spending(combined)

        console = Console()

        # =========================
        # 1. SUMMARY TABLE
        # =========================
        summary = Table(box=box.SIMPLE_HEAVY)
        summary.add_column("Category", style="bold")
        summary.add_column("Total", justify="right")
        summary.add_column("% Income", justify="right")

        summary.add_row("Income", f"[green]{self.fmt_money(vals['income'])}", "—")
        summary.add_row("Necessities", f"[red]{self.fmt_money(vals['necessities'][0])}", self.fmt_percent(vals['necessities'][1]))
        summary.add_row("Discretionary", f"[red]{self.fmt_money(vals['discretionary'][0])}", self.fmt_percent(vals['discretionary'][1]))
        summary.add_row("Savings", f"[green]{self.fmt_money(vals['savings'][0])}", self.fmt_percent(vals['savings'][1]))
        if vals['remaining'][0] < 0:
            summary.add_row("Remaining", f"[red]{self.fmt_money(vals['remaining'][0])}", self.fmt_percent(vals['remaining'][1]))
        else:
            summary.add_row("Remaining", f"[green]{self.fmt_money(vals['remaining'][0])}", self.fmt_percent(vals['remaining'][1]))

        income = vals["income"]

        # =========================
        # 2. TOP SPENDING TABLE
        # =========================
        top_table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
        top_table.add_column("#", justify="right")
        top_table.add_column("Category")
        top_table.add_column("Sub-Category")
        top_table.add_column("Amount", justify="right")
        top_table.add_column("% Income", justify="right")

        for i, (_, row) in enumerate(spending_sub_cat.head(5).iterrows(), 1):
            pct = row["amount"] / income if income != 0 else 0
            top_table.add_row(
                str(i),
                row["category"],
                row["sub-category"],
                self.fmt_money(row["amount"]),
                self.fmt_percent(pct)
            )

        top_panel = Panel(Align.center(top_table), title="Top Spending", border_style="magenta")

        # =========================
        # 3. BUDGET HEALTH PANEL
        # =========================
        savings_rate = vals["savings"][1]
        discretionary_rate = vals["discretionary"][1]
        leftover = vals["remaining"][0]

        if savings_rate >= 0.2:
            health_msg = "[green]Strong savings rate[/green]"
        elif savings_rate >= 0.1:
            health_msg = "[yellow]Moderate savings rate[/yellow]"
        else:
            health_msg = "[red]Low savings rate[/red]"

        if discretionary_rate > 0.4:
            health_msg += "\n[red]Too much discretionary spending![/red]"
        elif 0.3 <= discretionary_rate <= 0.4:
            health_msg += "\n[yellow]Check discretionary spending[/yellow]"
        elif 0.2 < discretionary_rate < 0.3:
            health_msg += "\n[green]Good discretionary spending[/green]"
        else:
            health_msg += "\n[red]Spend some money on yourself![/red]"

        if leftover < 0:
            health_msg += "\n[red]Overspending![/red]"

        health_panel = Panel(
            health_msg,
            title="Budget Health",
            border_style="green"
        )

        # 4. Highest frequency origins
        freqs, percent_freqs = self.highest_frequency_origins(combined)

        freq_table = Table(box=box.SIMPLE, style="yellow", pad_edge=False)
        freq_table.add_column("Origin")
        freq_table.add_column("# Txns", justify="right")
        freq_table.add_column("% Total Txns", justify="right")

        for value, count in freqs.head().items():
            percent = percent_freqs[value]
            freq_table.add_row(value, str(count), self.fmt_percent(percent))
        
        freq_table_panel = Panel(
            freq_table, title="Top Txn Origins", border_style="yellow"
        )

        # =========================
        # LAYOUT OUTPUT
        # =========================
        console.print(Align.center("\n[bold underline]BUDGET DASHBOARD[/bold underline]\n"))

        console.print(Align.center(summary))
        console.print()
        console.print(Align.center(Columns([freq_table_panel, health_panel])))
        console.print()
        console.print(top_panel)

    def generate_html_report(self, combined: pd.DataFrame, start_date: datetime | None, end_date: datetime):
        self.logger.info("Generating HTML report...")

        vals = self.caclulate_values(combined)
        spending_sub_cat, _ = self.group_spending(combined)
        freqs, percent_freqs = self.highest_frequency_origins(combined)

        # Prepare data for HTML template
        report_data = {
            "start_date": start_date if start_date else end_date.replace(day=1).strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "summary": [
                {"category": "Income", "total": self.fmt_money(vals['income']), "percent_income": "-"},
                {"category": "Necessities", "total": self.fmt_money(vals['necessities'][0]), "percent_income": self.fmt_percent(vals['necessities'][1])},
                {"category": "Discretionary", "total": self.fmt_money(vals['discretionary'][0]), "percent_income": self.fmt_percent(vals['discretionary'][1])},
                {"category": "Savings", "total": self.fmt_money(vals['savings'][0]), "percent_income": self.fmt_percent(vals['savings'][1])},
                {"category": "Remaining", "total": self.fmt_money(vals['remaining'][0]), "percent_income": self.fmt_percent(vals['remaining'][1])}
            ],
            "top_spending": [
                {
                    "rank": i,
                    "category": row["category"],
                    "sub_category": row["sub-category"],
                    "amount": self.fmt_money(row["amount"]),
                    "percent_income": self.fmt_percent(row["amount"] / vals['income'] if vals['income'] != 0 else 0)
                }
                for i, (_, row) in enumerate(spending_sub_cat.head(5).iterrows(), 1)
            ],
            "top_origins": [
                {
                    "origin": value,
                    "count": count,
                    "percent_total_txns": self.fmt_percent(percent)
                }
                for value, count in freqs.head().items()
                for percent in [percent_freqs[value]]
            ]
        }

        # Load Jinja2 template
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('report.html')

        # Render HTML
        html_content = template.render(report_data)

        # Save HTML to file

        report_dir = "reports/monthly_budget_report_" + end_date.strftime("%Y-%m-%d")
        if start_date:
            report_dir = "reports/monthly_budget_report_" + start_date.strftime("%Y-%m-%d") + "_" + end_date.strftime("%Y-%m-%d")

        os.makedirs(report_dir, exist_ok=True)
        with open(os.path.join(report_dir, 'report.html'), 'w') as f:
            f.write(html_content)

        self.logger.info(f"HTML report saved to {os.path.join(report_dir, 'report.html')}")
