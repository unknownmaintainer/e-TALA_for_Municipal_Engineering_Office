"""
Migration 0003: Add full workflow models
- Barangay: district, created_at, updated_at
- EngineeringRecord (new table): project_scope, year, completion_stats property
- PermitDetail (new table)
- ProjectDetail (new table)
- Document: requirement_item FK
- RequirementTemplate (new table)
- RequirementItem (new table)
- RecordRequirement (new table)
- CustomUser: role choices update (remove engineer)
"""
import django.db.models.deletion
import django.utils.timezone
import cloudinary_storage.storage
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permits', '0002_rename_permit_number_to_archive_number'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [

        # ── Barangay: add district + timestamps ──────────────────────────────
        migrations.AddField(
            model_name='barangay',
            name='district',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='barangay',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='barangay',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # ── CustomUser: update role choices (remove engineer) ────────────────
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[('staff', 'Engineering Staff'), ('admin', 'Administrator')],
                default='staff',
                max_length=20,
            ),
        ),

        # ── EngineeringRecord (new table) ─────────────────────────────────────
        migrations.CreateModel(
            name='EngineeringRecord',
            fields=[
                ('record_id', models.AutoField(primary_key=True, serialize=False)),
                ('record_type', models.CharField(
                    choices=[('Permit', 'Permit'), ('Project', 'Project')],
                    max_length=10,
                )),
                ('project_scope', models.CharField(
                    blank=True,
                    choices=[('Municipal', 'Municipal'), ('Barangay', 'Barangay')],
                    default='',
                    help_text='Municipal or Barangay — only applies to Project records.',
                    max_length=20,
                )),
                ('title', models.CharField(max_length=255)),
                ('year', models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text='Year of the record / permit.',
                )),
                ('description', models.TextField(blank=True, default='')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('active', 'Active'),
                        ('in_progress', 'In Progress'),
                        ('completed', 'Completed'),
                        ('archived', 'Archived'),
                    ],
                    default='active',
                    max_length=20,
                )),
                ('date_started', models.DateField(blank=True, null=True)),
                ('date_completed', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('barangay', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='engineering_records',
                    to='permits.barangay',
                )),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='engineering_records',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='engineeringrecord',
            index=models.Index(fields=['record_type'], name='permits_eng_record__type_idx'),
        ),
        migrations.AddIndex(
            model_name='engineeringrecord',
            index=models.Index(fields=['project_scope'], name='permits_eng_proj_scope_idx'),
        ),
        migrations.AddIndex(
            model_name='engineeringrecord',
            index=models.Index(fields=['barangay'], name='permits_eng_barangay_idx'),
        ),
        migrations.AddIndex(
            model_name='engineeringrecord',
            index=models.Index(fields=['status'], name='permits_eng_status_idx'),
        ),
        migrations.AddIndex(
            model_name='engineeringrecord',
            index=models.Index(fields=['year'], name='permits_eng_year_idx'),
        ),
        migrations.AddIndex(
            model_name='engineeringrecord',
            index=models.Index(fields=['title'], name='permits_eng_title_idx'),
        ),
        migrations.AddIndex(
            model_name='engineeringrecord',
            index=models.Index(fields=['-created_at'], name='permits_eng_created_idx'),
        ),

        # ── PermitDetail (new table) ──────────────────────────────────────────
        migrations.CreateModel(
            name='PermitDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('permit_type', models.CharField(
                    choices=[
                        ('Building', 'Building'),
                        ('Electrical', 'Electrical'),
                        ('Occupancy', 'Occupancy'),
                        ('Fencing', 'Fencing'),
                        ('Demolition', 'Demolition'),
                        ('Renovation', 'Renovation'),
                    ],
                    max_length=30,
                )),
                ('building_type', models.CharField(
                    blank=True,
                    choices=[
                        ('Residential', 'Residential'),
                        ('Commercial', 'Commercial'),
                        ('Industrial', 'Industrial'),
                        ('Institutional', 'Institutional'),
                        ('Agricultural', 'Agricultural'),
                    ],
                    default='',
                    max_length=30,
                )),
                ('permit_number', models.CharField(blank=True, default='', max_length=100)),
                ('applicant_name', models.CharField(blank=True, default='', max_length=255)),
                ('resolution_required', models.BooleanField(default=False)),
                ('remarks', models.TextField(blank=True, default='')),
                ('engineering_record', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='permit_detail',
                    to='permits.engineeringrecord',
                )),
            ],
        ),

        # ── ProjectDetail (new table) ─────────────────────────────────────────
        migrations.CreateModel(
            name='ProjectDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('project_type', models.CharField(
                    choices=[
                        ('Road & Bridge', 'Road & Bridge'),
                        ('Building', 'Building'),
                        ('Water System', 'Water System'),
                        ('Flood Control', 'Flood Control'),
                        ('Drainage', 'Drainage'),
                        ('Multi-purpose Hall', 'Multi-purpose Hall'),
                        ('Others', 'Others'),
                    ],
                    max_length=50,
                )),
                ('funding_source', models.CharField(blank=True, default='', max_length=255)),
                ('contractor', models.CharField(blank=True, default='', max_length=255)),
                ('project_cost', models.DecimalField(
                    blank=True, decimal_places=2, max_digits=15, null=True,
                )),
                ('project_status', models.CharField(
                    choices=[
                        ('Planning', 'Planning'),
                        ('Procurement', 'Procurement'),
                        ('Ongoing', 'Ongoing'),
                        ('Completed', 'Completed'),
                        ('Suspended', 'Suspended'),
                    ],
                    default='Planning',
                    max_length=20,
                )),
                ('engineering_record', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='project_detail',
                    to='permits.engineeringrecord',
                )),
            ],
        ),

        # ── RequirementTemplate (new table) ───────────────────────────────────
        migrations.CreateModel(
            name='RequirementTemplate',
            fields=[
                ('template_id', models.AutoField(primary_key=True, serialize=False)),
                ('record_type', models.CharField(
                    choices=[('Permit', 'Permit'), ('Project', 'Project')],
                    max_length=10,
                )),
                ('subtype', models.CharField(
                    help_text='E.g. "Building", "Road & Bridge", "Flood Control"',
                    max_length=50,
                )),
                ('scope', models.CharField(
                    blank=True,
                    choices=[('', 'N/A (Permit)'), ('Municipal', 'Municipal'), ('Barangay', 'Barangay')],
                    default='',
                    help_text='Municipal or Barangay for projects; blank for permits.',
                    max_length=20,
                )),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['record_type', 'subtype'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='requirementtemplate',
            unique_together={('record_type', 'subtype', 'scope')},
        ),

        # ── RequirementItem (new table) ────────────────────────────────────────
        migrations.CreateModel(
            name='RequirementItem',
            fields=[
                ('item_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_required', models.BooleanField(default=True)),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='permits.requirementtemplate',
                )),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),

        # ── Document: add requirement_item FK and version ─────────────────────
        migrations.AddField(
            model_name='document',
            name='requirement_item',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='documents',
                to='permits.requirementitem',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='version',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='document',
            name='engineering_record',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='documents',
                to='permits.engineeringrecord',
            ),
        ),

        # ── RecordRequirement (new table) ──────────────────────────────────────
        migrations.CreateModel(
            name='RecordRequirement',
            fields=[
                ('req_id', models.AutoField(primary_key=True, serialize=False)),
                ('is_fulfilled', models.BooleanField(default=False)),
                ('fulfilled_at', models.DateTimeField(blank=True, null=True)),
                ('document', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='record_requirement',
                    to='permits.document',
                )),
                ('fulfilled_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='fulfilled_requirements',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('record', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='requirements',
                    to='permits.engineeringrecord',
                )),
                ('requirement_item', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='record_requirements',
                    to='permits.requirementitem',
                )),
            ],
            options={
                'ordering': ['requirement_item__order', 'requirement_item__name'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='recordrequirement',
            unique_together={('record', 'requirement_item')},
        ),

    ]
