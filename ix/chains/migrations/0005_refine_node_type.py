# Generated by Django 4.2.2 on 2023-06-20 00:17

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("chains", "0004_remove_chain_roots"),
    ]

    operations = [
        migrations.CreateModel(
            name="NodeType",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(null=True)),
                ("class_path", models.CharField(max_length=255)),
                ("type", models.CharField(max_length=255)),
                (
                    "display_type",
                    models.CharField(
                        choices=[("node", "node"), ("list", "list"), ("map", "map")],
                        default="node",
                        max_length=10,
                    ),
                ),
                ("connectors", models.JSONField(null=True)),
                ("fields", models.JSONField(null=True)),
                ("child_field", models.CharField(max_length=32, null=True)),
            ],
        ),
        migrations.DeleteModel(
            name="ChainNodeType",
        ),
    ]