# Adapters

Adapters are **optional** framework integrations. The booking engine itself is
framework-agnostic — adapters simply translate ORM models into the DTOs the engine expects.

For full docstrings see `src/codex_tools/adapters/`.

## Django adapter (optional helper)

Install: `pip install codex-tools[django]`

`DjangoAvailabilityAdapter` bridges any Django ORM models to the booking engine.
You pass your model classes on initialization; the adapter handles scheduling queries.

```python
from codex_tools.adapters.django.booking_adapter import DjangoAvailabilityAdapter

adapter = DjangoAvailabilityAdapter(
    master_model=Master,
    appointment_model=Appointment,
    service_model=Service,
    day_off_model=DayOff,
    booking_settings_model=BookingSettings,
    site_settings_model=SiteSettings,
    step_minutes=30,
    appointment_status_filter=["pending", "confirmed"],
)

availability = adapter.build_masters_availability(master_ids=[1, 2], target_date=date.today())
request = adapter.build_engine_request(service_ids=[5], target_date=date.today())
```

### Customizing field access

Subclass the adapter and override the field accessor methods to use different model
field names without changing the core scheduling logic:

```python
class MyAdapter(DjangoAvailabilityAdapter):
    def get_work_start(self, master):
        return master.schedule_start       # custom field name

    def get_master_timezone(self, master) -> str:
        return master.location.tz_name     # resolve from related model
```

### Django model mixins

`BookableMasterMixin` and `BookableServiceMixin` add the expected fields to your models.
They are a convenience — you can use the adapter without them by overriding the accessors above.

```python
from codex_tools.adapters.django.mixins import BookableMasterMixin, BookableServiceMixin

class Master(BookableMasterMixin, models.Model):
    timezone = models.CharField(default="Europe/Berlin", ...)  # override UTC default

class Service(BookableServiceMixin, models.Model):
    ...
```
