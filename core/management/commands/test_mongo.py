"""
Diagnose MongoDB Atlas connectivity issues.
Run: python manage.py test_mongo
"""
import sys
import ssl
import socket
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Test MongoDB Atlas connection and diagnose SSL/TLS issues'

    def handle(self, *args, **options):
        uri = settings.MONGO_URI
        db_name = settings.MONGO_DB_NAME

        self.stdout.write('\n== SmartServe MongoDB Diagnostics ====================')
        self.stdout.write(f'URI prefix : {uri[:50]}...')
        self.stdout.write(f'Database   : {db_name}')
        self.stdout.write(f'Python SSL : {ssl.OPENSSL_VERSION}')

        # 1. DNS resolution via dnspython
        self.stdout.write('\n[1] DNS / SRV resolution...')
        try:
            import dns.resolver
            host = uri.split('@')[-1].split('/')[0].split('?')[0]
            answers = dns.resolver.resolve(f'_mongodb._tcp.{host}', 'SRV')
            targets = [str(r.target) for r in answers]
            self.stdout.write(self.style.SUCCESS(f'    OK -- SRV targets: {targets[:2]}'))
        except ImportError:
            self.stdout.write('    (dnspython not installed -- skipping SRV check)')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'    DNS: {e}'))

        # 2. Actual pymongo ping
        self.stdout.write('\n[2] MongoDB ping (5 s timeout)...')
        from pymongo import MongoClient
        from pymongo.errors import ServerSelectionTimeoutError

        try:
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                tls=True,
            )
            client.admin.command('ping')
            client.close()
            self.stdout.write(self.style.SUCCESS('    OK -- connected and pinged successfully!'))
            self.stdout.write('\n[OK] MongoDB is reachable. No issues found.\n')
            return
        except ServerSelectionTimeoutError as e:
            err_str = str(e)
            self.stdout.write(self.style.ERROR(f'    FAIL -- {err_str[:200]}'))

        # 3. Retry with relaxed TLS (diagnoses cert vs IP issue)
        self.stdout.write('\n[3] Retry with tlsAllowInvalidCertificates=True...')
        try:
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                tls=True,
                tlsAllowInvalidCertificates=True,
            )
            client.admin.command('ping')
            client.close()
            self.stdout.write(self.style.WARNING(
                '    Connected with relaxed TLS -- certificate validation failing.\n'
                '    Fix: pip install --upgrade certifi\n'
                '    Or add MONGO_TLS_ALLOW_INVALID=True to .env (dev only)'
            ))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'    Also failed -- {str(e)[:100]}'))

        # 4. Final diagnosis
        self.stdout.write('\n== DIAGNOSIS =========================================')
        self.stdout.write(self.style.ERROR(
            '\n[FAIL] Cannot reach MongoDB Atlas. Most likely causes:\n\n'
            '  1. YOUR IP IS NOT WHITELISTED\n'
            '     -> Log in to cloud.mongodb.com\n'
            '     -> Go to: Security -> Network Access\n'
            '     -> Click "Add IP Address"\n'
            '     -> Click "Add Current IP Address" (or 0.0.0.0/0 for dev)\n'
            '     -> Confirm and wait ~30 seconds\n\n'
            '  2. YOUR ATLAS CLUSTER IS PAUSED (free tier auto-pauses)\n'
            '     -> Log in to cloud.mongodb.com\n'
            '     -> Find your cluster -> click "Resume"\n'
            '     -> Wait 1-2 minutes for it to start\n\n'
            '  3. LOCAL NETWORK / FIREWALL blocks port 27017\n'
            '     -> Try on a different network (mobile hotspot)\n\n'
            'After fixing Atlas, re-run: python manage.py test_mongo\n'
        ))
        sys.exit(1)
