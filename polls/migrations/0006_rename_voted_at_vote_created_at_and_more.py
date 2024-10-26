# Generated by Django 5.1.2 on 2024-10-26 06:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('polls', '0005_poll_multi_option'),
    ]

    operations = [
        migrations.RenameField(
            model_name='vote',
            old_name='voted_at',
            new_name='created_at',
        ),
        migrations.AlterUniqueTogether(
            name='vote',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='vote',
            name='attempts',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='vote',
            name='option',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='polls.option'),
        ),
        migrations.AlterField(
            model_name='vote',
            name='poll',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='polls.poll'),
        ),
    ]
