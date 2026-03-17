"""
codex_platform.adapters.django.mixins
====================================
Optional Django mixins to standardize models
to the requirements of the booking engine.

Requires: pip install codex-tools[django]

Applying to the Master model:
    from codex_platform.adapters.django.mixins import BookableMasterMixin

    class Master(BookableMasterMixin, TimestampMixin, models.Model):
        name = models.CharField(...)
        # BookableMasterMixin will add the required fields automatically

Applying to the Service model:
    from codex_platform.adapters.django.mixins import BookableServiceMixin

    class Service(BookableServiceMixin, TimestampMixin, models.Model):
        title = models.CharField(...)
        # BookableServiceMixin will add min_gap_after_minutes

IMPORTANT: fields with null=True — if not set on a specific instance,
DjangoAvailabilityAdapter will automatically get defaults from BookingSettings.
"""

from django.db import models


class BookableMasterMixin(models.Model):
    """Mixin for the performer model (master, specialist, resource).

    Adds fields necessary for the engine to properly calculate slots.
    All fields are nullable — if not set, the adapter uses global
    defaults from BookingSettings.

    Priority logic (in DjangoAvailabilityAdapter):
        master.work_start is not None  -> use it
        master.work_start is None      -> take BookingSettings.default_work_start_weekdays

    Fields:
        work_start (TimeField, nullable):
            Start of the master's workday. Overrides the salon's global schedule.

        work_end (TimeField, nullable):
            End of the master's workday.

        break_start (TimeField, nullable):
            Start of break (lunch etc.). None = no break.

        break_end (TimeField, nullable):
            End of break.

        buffer_between_minutes (PositiveIntegerField, nullable):
            Time in minutes between clients. The master needs this time
            to prepare for the next client (cleaning, instruments).
            None -> BookingSettings.default_buffer_between_minutes.

        min_advance_minutes (PositiveIntegerField, nullable):
            Minimum minutes in advance a booking can be made.
            None -> BookingSettings.default_min_advance_minutes.

        max_advance_days (PositiveIntegerField, nullable):
            Booking horizon in days. Cannot book further than N days ahead.
            None -> BookingSettings.default_max_advance_days.

        timezone (CharField):
            IANA timezone string for this master (e.g. "Europe/Berlin", "America/New_York").
            Override to your project's timezone — defaults to "UTC".
            Used for timezone-aware slot calculation; the adapter does NOT rely on
            global settings.TIME_ZONE.

    Usage example in the administration:
        - Master A works 9:00-18:00, no individual settings -> take from the salon
        - Master B works 12:00-20:00 -> set work_start=12:00, work_end=20:00
        - Master C takes a 15 min break between clients -> buffer_between_minutes=15
    """

    # Individual workday (override SiteSettings global schedule)
    work_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Work Start",
        help_text="Individual work start time. If empty, uses salon schedule.",
    )
    work_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Work End",
        help_text="Individual work end time. If empty, uses salon schedule.",
    )

    # Break (lunch, personal time)
    break_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Break Start",
        help_text="Break start time (lunch etc). Leave empty if no break.",
    )
    break_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Break End",
        help_text="Break end time.",
    )

    # Buffers and booking horizons
    buffer_between_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Buffer Between Clients (min)",
        help_text="Minutes needed between clients for preparation. If empty, uses global default from Booking Settings.",  # noqa: E501
    )
    min_advance_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Min Advance Booking (min)",
        help_text="Minimum minutes before appointment start a booking can be made. If empty, uses global default.",
    )
    max_advance_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Max Advance Booking (days)",
        help_text="How many days in advance a booking can be made. If empty, uses global default.",
    )

    max_clients_parallel = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Max Parallel Clients",
        help_text=(
            "How many clients this master can serve simultaneously. "
            "1 = one at a time (default). "
            "2+ = group booking support (e.g. couples pedicure). "
            "Used with BookingEngineRequest.group_size."
        ),
    )

    timezone = models.CharField(
        max_length=64,
        default="UTC",
        verbose_name="Timezone",
        help_text=(
            "IANA timezone for this master (e.g. 'Europe/Berlin', 'America/New_York'). "
            "Override to your project's timezone — defaults to 'UTC'. "
            "Used for timezone-aware slot calculation. "
            "The adapter will NOT rely on global settings.TIME_ZONE."
        ),
    )

    class Meta:
        abstract = True


class BookableServiceMixin(models.Model):
    """Mixin for the service model.

    Adds fields for proper chain calculation in ChainFinder.

    Fields:
        min_gap_after_minutes (PositiveIntegerField, default=0):
            Minimum pause in minutes AFTER this service
            before the next one in the chain.

            Examples:
                - Manicure -> Pedicure: min_gap_after_minutes=0 (move immediately)
                - Coloring -> Haircut: min_gap_after_minutes=30 (wait 30 min)
                - Base -> Top coat: min_gap_after_minutes=15 (drying)

            ChainFinder considers this field when looking for the next slot:
            next_service.start >= current_service.end + min_gap_after_minutes

        parallel_ok (BooleanField, default=True):
            Can this service be performed in parallel with other services
            in a single chain (by different masters simultaneously).
            True  -> manicure + pedicure simultaneously is OK.
            False -> service requires sequential execution
                     (e.g. after the previous one: drying -> top coat).
            DjangoAvailabilityAdapter reads this field and passes it to ServiceRequest.parallel_group.

    Usage example:
        class Service(BookableServiceMixin, models.Model):
            title = CharField(...)
            duration = PositiveIntegerField(...)
            # + min_gap_after_minutes, parallel_ok added by mixin
    """

    min_gap_after_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name="Gap After Service (min)",
        help_text=(
            "Minimum pause in minutes after this service before the next one "
            "in a chain booking (e.g. drying time, waiting). Default: 0."
        ),
    )
    parallel_ok = models.BooleanField(
        default=True,
        verbose_name="Can Run in Parallel",
        help_text=(
            "Whether this service can be performed simultaneously with other services "
            "in a chain booking (by different masters). "
            "True = manicure + pedicure at the same time is OK. "
            "False = must be strictly sequential."
        ),
    )

    class Meta:
        abstract = True
