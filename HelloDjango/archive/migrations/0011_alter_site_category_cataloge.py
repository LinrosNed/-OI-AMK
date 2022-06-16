# Generated by Django 4.0.1 on 2022-05-11 17:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0010_site_languege'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='archive.sitecategoty', verbose_name='Категория сайта'),
        ),
        migrations.CreateModel(
            name='Cataloge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, verbose_name='Название каталога')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='archive.sitecategoty')),
            ],
        ),
    ]
