from django.core import mail
from django.core.management import call_command
from django_mailer import models
from base import MailerTestCase
import datetime


class TestCommands(MailerTestCase):
    """
    A test case for management commands provided by django-mailer.

    """
    def test_send_mail(self):
        """
        The ``send_mail`` command initiates the sending of messages in the
        queue.

        """
        # No action is taken if there are no messages.
        call_command('send_mail', verbosity='0')
        # Any (non-deferred) queued messages will be sent.
        self.queue_message()
        self.queue_message()
        self.queue_message(subject='deferred')
        models.QueuedMessage.objects\
                    .filter(message__subject__startswith='deferred')\
                    .update(deferred=datetime.datetime.now())
        queued_messages = models.QueuedMessage.objects.all()
        self.assertEqual(queued_messages.count(), 3)
        self.assertEqual(len(mail.outbox), 0)
        call_command('send_mail', verbosity='0')
        self.assertEqual(queued_messages.count(), 1)

    def test_retry_deferred(self):
        """
        The ``retry_deferred`` command places deferred messages back in the
        queue.

        """
        self.queue_message()
        self.queue_message(subject='deferred')
        self.queue_message(subject='deferred 2')
        self.queue_message(subject='deferred 3')
        models.QueuedMessage.objects\
                    .filter(message__subject__startswith='deferred')\
                    .update(deferred=datetime.datetime.now())
        non_deferred_messages = models.QueuedMessage.objects.non_deferred()
        # Deferred messages are returned to the queue (nothing is sent).
        self.assertEqual(non_deferred_messages.count(), 1)
        call_command('retry_deferred', verbosity='0')
        self.assertEqual(non_deferred_messages.count(), 4)
        self.assertEqual(len(mail.outbox), 0)
        # Check the --max-retries logic.
        models.QueuedMessage.objects\
                    .filter(message__subject='deferred')\
                    .update(deferred=datetime.datetime.now(), retries=2)
        models.QueuedMessage.objects\
                    .filter(message__subject='deferred 2')\
                    .update(deferred=datetime.datetime.now(), retries=3)
        models.QueuedMessage.objects\
                    .filter(message__subject='deferred 3')\
                    .update(deferred=datetime.datetime.now(), retries=4)
        self.assertEqual(non_deferred_messages.count(), 1)
        call_command('retry_deferred', verbosity='0', max_retries=3)
        self.assertEqual(non_deferred_messages.count(), 3)

    def test_status_mail(self):
        """
        The ``status_mail`` should return a string that matches:
            (?P<queued>\d+)/(?P<deferred>\d+)/(?P<seconds>\d+)
        """
        import re
        import sys
        from cStringIO import StringIO
        import time

        re_string  = r"(?P<queued>\d+)/(?P<deferred>\d+)/(?P<seconds>\d+)"
        p = re.compile(re_string)

        self.queue_message(subject="test")
        self.queue_message(subject='deferred')
        self.queue_message(subject='deferred 2')
        self.queue_message(subject='deferred 3')
        models.QueuedMessage.objects\
                    .filter(message__subject__startswith='deferred')\
                    .update(deferred=datetime.datetime.now())
        non_deferred_messages = models.QueuedMessage.objects.non_deferred()
        time.sleep(1)
        # Deferred messages are returned to the queue (nothing is sent).
        out, sys.stdout = sys.stdout, StringIO()
        with self.assertRaises(SystemExit) as cm:
            call_command('status_mail', verbosity='0')
        sys.stdout.seek(0)
        result = sys.stdout.read()
        m = p.match(result)
        sys.stdout = out
        self.assertTrue(m, "Output does not include expected r.e.")
        v = m.groupdict()
        self.assertTrue(v['queued'], "1")
        self.assertEqual(v['deferred'], "3")
        self.assertTrue(int(v['seconds'])>=1)

    def test_cleanup_mail(self):
        """
        The ``cleanup_mail`` command deletes mails older than a specified
        amount of days
        """
        today = datetime.date.today()
        self.assertEqual(models.Message.objects.count(), 0)
        #new message (not to be deleted)
        models.Message.objects.create()
        prev = today - datetime.timedelta(31)
        # new message (old)
        models.Message.objects.create(date_created=prev)
        call_command('cleanup_mail', days=30)
        self.assertEqual(models.Message.objects.count(), 1)
