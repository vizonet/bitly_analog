# Generated by Django 2.2.21 on 2021-05-09 19:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_auto_20210508_1319'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='url',
            name='short',
        ),
        migrations.AddField(
            model_name='url',
            name='alias',
            field=models.CharField(default='', max_length=100, verbose_name='Алиас'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='url',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='app.Owner'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='collection',
            name='url',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='app.Url'),
        ),
        migrations.AlterField(
            model_name='owner',
            name='trows_on_page',
            field=models.PositiveSmallIntegerField(default=3, verbose_name='Число строк таблицы правил на странице'),
        ),
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_time', models.DateTimeField(verbose_name='Дата и время операции')),
                ('process', models.CharField(max_length=100, verbose_name='Имя процесса')),
                ('execute', models.TextField(verbose_name='Что выполнено')),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.Owner')),
            ],
        ),
    ]