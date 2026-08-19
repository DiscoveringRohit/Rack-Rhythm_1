from django.core.management.base import BaseCommand
from janSetu.models import State, City, Ward

class Command(BaseCommand):
    help = 'Seeds the database with sample address hierarchy for Odisha -> Bhubaneswar'

    def handle(self, *args, **options):
        state, created = State.objects.get_or_create(name='Odisha')
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created State: {state.name}'))

        city, created = City.objects.get_or_create(name='Bhubaneswar', state=state)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created City: {city.name}'))

        ward, created = Ward.objects.get_or_create(
            name='ITER College Road / Jagmohan Nagar',
            ward_number=63,
            city=city,
            defaults={'pincode': '751030'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Ward: {ward.name}'))
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded address data.'))
