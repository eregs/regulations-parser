import click

from regparser.index.xml_sync import sync


@click.command()
def sync_xml():
    """Synchronize modified XML. Checkout/pull down the latest modified XML
    files. If one has been modified, it will notify later steps that they need
    to be rebuilt"""
    sync()
