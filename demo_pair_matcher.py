#!/usr/bin/env python3
"""
Demo script showing the Pair Matcher functionality.

This script demonstrates how the pair matcher resolves human-readable
trading pair names to official Kraken pair codes.
"""

from pair_matcher import find_pair_match, find_similar_pairs
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def demo_basic_matching():
    """Demonstrate basic pair matching."""
    console.print("\n[bold cyan]Demo 1: Basic Pair Matching[/bold cyan]\n")
    
    test_inputs = [
        'BTC/USD',
        'btc/usd',
        'BTCUSD',
        'ETH/USDT',
        'eth-usdt',
        'SOL/EUR',
        'ada/usd',
    ]
    
    table = Table(title="Human-Readable Input → Kraken Code", box=box.ROUNDED)
    table.add_column("Input", style="cyan")
    table.add_column("Resolved Code", style="green")
    table.add_column("Kraken wsname", style="yellow")
    table.add_column("Match Type", style="blue")
    table.add_column("Confidence", justify="right")
    
    for human_input in test_inputs:
        result = find_pair_match(human_input)
        if result:
            confidence_color = "green" if result.confidence >= 0.9 else "yellow"
            table.add_row(
                human_input,
                result.pair_code,
                result.kraken_wsname,
                result.match_type,
                f"[{confidence_color}]{result.confidence:.0%}[/{confidence_color}]"
            )
        else:
            table.add_row(human_input, "[red]NO MATCH[/red]", "", "", "")
    
    console.print(table)


def demo_exact_vs_normalized():
    """Demonstrate the difference between exact and normalized matches."""
    console.print("\n[bold cyan]Demo 2: Exact vs Normalized Matches[/bold cyan]\n")
    
    examples = [
        ('XXBTZUSD', 'Already an official code → Exact match'),
        ('BTC/USD', 'Human-readable format → Normalized to XXBTZUSD'),
        ('XETHZUSD', 'Already an official code → Exact match'),
        ('ETH/USD', 'Human-readable format → Normalized to XETHZUSD'),
    ]
    
    for input_str, description in examples:
        result = find_pair_match(input_str)
        if result:
            match_type_color = "green" if result.is_exact() else "yellow"
            console.print(f"  • [cyan]{input_str:12}[/cyan] → [{match_type_color}]{result.pair_code:12}[/{match_type_color}] ({description})")


def demo_fuzzy_matching():
    """Demonstrate fuzzy matching with similar pairs."""
    console.print("\n[bold cyan]Demo 3: Fuzzy Matching (Finding Similar Pairs)[/bold cyan]\n")
    
    test_input = "BTC"
    console.print(f"Searching for pairs similar to: [cyan]'{test_input}'[/cyan]\n")
    
    results = find_similar_pairs(test_input, limit=10)
    
    table = Table(title=f"Top 10 Matches for '{test_input}'", box=box.ROUNDED)
    table.add_column("Rank", justify="right", style="cyan")
    table.add_column("Pair Code", style="green")
    table.add_column("Kraken wsname", style="yellow")
    table.add_column("Confidence", justify="right")
    
    for i, result in enumerate(results[:10], 1):
        confidence_color = "green" if result.confidence >= 0.9 else "yellow" if result.confidence >= 0.7 else "red"
        table.add_row(
            str(i),
            result.pair_code,
            result.kraken_wsname,
            f"[{confidence_color}]{result.confidence:.0%}[/{confidence_color}]"
        )
    
    console.print(table)


def demo_format_variations():
    """Demonstrate that different input formats resolve to the same pair."""
    console.print("\n[bold cyan]Demo 4: Format Variations (All Resolve to Same Pair)[/bold cyan]\n")
    
    variations = [
        'BTC/USD',
        'btc/usd',
        'BTCUSD',
        'BTC-USD',
        'btc usd',
        'Btc/Usd',
    ]
    
    results = []
    for var in variations:
        result = find_pair_match(var)
        if result:
            results.append((var, result.pair_code))
    
    # Group by resolved code
    resolved_code = results[0][1] if results else "N/A"
    
    console.print(f"  All these inputs resolve to: [green bold]{resolved_code}[/green bold]\n")
    for input_str, code in results:
        console.print(f"    • [cyan]{input_str:12}[/cyan] → {code}")


def demo_csv_editor_integration():
    """Explain CSV editor integration."""
    console.print("\n[bold cyan]Demo 5: CSV Editor Integration[/bold cyan]\n")
    
    info = """
[yellow]How it works in the CSV Editor:[/yellow]

1. Open the CSV editor: [cyan]uv run python3 csv_editor.py config.csv[/cyan]
2. Navigate to a "pair" field
3. Press [cyan]Enter[/cyan] or [cyan]'e'[/cyan] to edit
4. Type a human-readable name like: [green]BTC/USD[/green]
5. Press [cyan]Enter[/cyan] to save

[yellow]What happens:[/yellow]
• Editor automatically resolves [green]BTC/USD[/green] → [green]XXBTZUSD[/green]
• Shows confirmation: [green]✓ Resolved to: XXBTZUSD[/green]
• Saves the official Kraken code to the CSV file

[yellow]Match confidence indicators:[/yellow]
• [green]100%[/green] confidence - Exact or normalized match
• [yellow]70-90%[/yellow] confidence - Fuzzy match with warning
• [red]<70%[/red] confidence - Rejected (too uncertain)
    """
    
    console.print(Panel(info, border_style="cyan"))


def demo_special_cases():
    """Demonstrate special cases like BTC vs XBT."""
    console.print("\n[bold cyan]Demo 6: Special Cases[/bold cyan]\n")
    
    console.print("[yellow]Kraken uses XBT (not BTC) for Bitcoin:[/yellow]\n")
    
    btc_cases = [
        ('BTC/USD', 'XXBTZUSD', 'Base: XXBT, Quote: ZUSD'),
        ('BTC/USDT', 'XBTUSDT', 'Base: XXBT, Quote: USDT'),
        ('BTC/EUR', 'XXBTZEUR', 'Base: XXBT, Quote: ZEUR'),
    ]
    
    for human_input, pair_code, explanation in btc_cases:
        console.print(f"  • [cyan]{human_input:10}[/cyan] → [green]{pair_code:10}[/green] ({explanation})")
    
    console.print("\n[yellow]Different USD variations:[/yellow]\n")
    
    usd_cases = [
        ('BTC/USD', 'XXBTZUSD', 'Regular USD (ZUSD)'),
        ('BTC/USDT', 'XBTUSDT', 'Tether USD stablecoin'),
        ('BTC/USDC', 'XBTUSDC', 'USD Coin stablecoin'),
    ]
    
    for human_input, pair_code, explanation in usd_cases:
        console.print(f"  • [cyan]{human_input:10}[/cyan] → [green]{pair_code:10}[/green] ({explanation})")


def main():
    """Run all demos."""
    console.print("\n[bold magenta]═══════════════════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]     PAIR MATCHER - Human-Readable Trading Pairs      [/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════════════════[/bold magenta]")
    
    try:
        demo_basic_matching()
        demo_exact_vs_normalized()
        demo_format_variations()
        demo_special_cases()
        demo_fuzzy_matching()
        demo_csv_editor_integration()
        
        console.print("\n[bold green]✓ All demos completed successfully![/bold green]\n")
        console.print("[yellow]Try it yourself:[/yellow] [cyan]uv run python3 csv_editor.py config.csv[/cyan]\n")
        
    except Exception as e:
        console.print(f"\n[bold red]Error running demos:[/bold red] {e}\n")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
