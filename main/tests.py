from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Counterparty, Course, CourseTeacherAssignment, Enrollment, UserProfile, UserRole


def make_profile(username, role, **kwargs):
    user = User.objects.create_user(username=username, password='x')
    return UserProfile.objects.create(user=user, role=role, **kwargs)


def make_course(**kwargs):
    return Course.objects.create(
        name=kwargs.pop('name', 'Анги'), duration_weeks=12, price=0, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), **kwargs
    )


class RoleChangeTests(TestCase):
    def test_student_to_manager_and_back(self):
        student = make_profile('s1', UserRole.STUDENT)
        enrollment = Enrollment.objects.create(student=student, course=make_course(), status='APPROVED')

        student.role = UserRole.MANAGER
        student.save()
        student.user.refresh_from_db()
        enrollment.refresh_from_db()
        self.assertTrue(student.user.is_staff)
        self.assertFalse(enrollment.is_active)
        self.assertTrue(Enrollment.objects.filter(pk=enrollment.pk).exists())

        student.role = UserRole.STUDENT
        student.save()
        student.user.refresh_from_db()
        student.refresh_from_db()
        self.assertFalse(student.user.is_staff)
        self.assertTrue(student.is_active_student)

    def test_superuser_keeps_staff(self):
        profile = make_profile('boss', UserRole.DIRECTOR)
        profile.user.is_superuser = True
        profile.user.save()
        profile.role = UserRole.STUDENT
        profile.save()
        profile.user.refresh_from_db()
        self.assertTrue(profile.user.is_staff)

    def test_teacher_released_from_active_courses_only(self):
        teacher = make_profile('t1', UserRole.TEACHER_ADVANCED)
        active = make_course(name='Идэвхтэй', teacher=teacher)
        finished = make_course(name='Дууссан', teacher=teacher, is_active=False)
        CourseTeacherAssignment.objects.create(course=active, teacher=teacher)
        CourseTeacherAssignment.objects.create(course=finished, teacher=teacher)

        teacher.role = UserRole.MANAGER
        teacher.save()
        active.refresh_from_db()
        finished.refresh_from_db()
        self.assertIsNone(active.teacher)
        self.assertEqual(finished.teacher, teacher)
        self.assertEqual(list(CourseTeacherAssignment.objects.values_list('course', flat=True)), [finished.id])


class ConversionTests(TestCase):
    def setUp(self):
        self.admin = make_profile('admin', UserRole.DIRECTOR)
        self.client.force_login(self.admin.user)

    def test_counterparty_to_student(self):
        cp = Counterparty.objects.create(name='Бат', phone='9911-2233', counterparty_type='CUSTOMER')
        response = self.client.post(reverse('main:counterparty_to_student', args=[cp.id]))
        cp.refresh_from_db()
        self.assertIsNotNone(cp.profile)
        self.assertEqual(cp.profile.role, UserRole.STUDENT)
        self.assertEqual(cp.profile.phone, '99112233')
        self.assertRedirects(response, reverse('main:student_update', args=[cp.profile.id]), fetch_redirect_response=False)

        # Дахин дарахад шинэ хэрэглэгч үүсэхгүй
        count = UserProfile.objects.count()
        self.client.post(reverse('main:counterparty_to_student', args=[cp.id]))
        self.assertEqual(UserProfile.objects.count(), count)

    def test_counterparty_links_existing_profile_by_phone(self):
        student = make_profile('s2', UserRole.MANAGER, phone='88001122')
        cp = Counterparty.objects.create(name='Дорж', phone='88001122')
        self.client.post(reverse('main:counterparty_to_student', args=[cp.id]))
        cp.refresh_from_db()
        student.refresh_from_db()
        self.assertEqual(cp.profile, student)
        self.assertEqual(student.role, UserRole.STUDENT)

    def test_profile_to_counterparty(self):
        student = make_profile('s3', UserRole.STUDENT, last_name='Бат', first_name='Сараа', phone='99001122')
        Counterparty.objects.create(name='Бат Сараа', profile=make_profile('other', UserRole.STUDENT))
        self.client.post(reverse('main:profile_to_counterparty', args=[student.id]))
        cp = Counterparty.objects.get(profile=student)
        self.assertEqual(cp.name, 'Бат Сараа (99001122)')
        student.refresh_from_db()
        self.assertEqual(student.role, UserRole.STUDENT)

        self.client.post(reverse('main:profile_to_counterparty', args=[student.id]))
        self.assertEqual(Counterparty.objects.filter(profile=student).count(), 1)


class PasswordResetTests(TestCase):
    def test_reset_by_phone_sends_email_and_link_works(self):
        from django.core import mail

        profile = make_profile('s9', UserRole.STUDENT, phone='99887766', first_name='Сараа')
        profile.user.email = 'saraa@example.com'
        profile.user.save()

        response = self.client.post(reverse('main:password_reset'), {'email': '9988-7766'})
        self.assertRedirects(response, reverse('main:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['saraa@example.com'])

        link = next(line for line in mail.outbox[0].body.splitlines() if '/password-reset/' in line)
        path = link.split('://', 1)[1].split('/', 1)[1]
        response = self.client.get('/' + path, follow=True)
        response = self.client.post(response.redirect_chain[-1][0], {
            'new_password1': 'Shine-nuuts-2026', 'new_password2': 'Shine-nuuts-2026',
        })
        self.assertRedirects(response, reverse('main:password_reset_complete'))
        profile.user.refresh_from_db()
        self.assertTrue(profile.user.check_password('Shine-nuuts-2026'))

    def test_unknown_or_no_email_sends_nothing(self):
        from django.core import mail

        make_profile('s10', UserRole.STUDENT, phone='88776655')
        response = self.client.post(reverse('main:password_reset'), {'email': '88776655'})
        self.assertContains(response, 'имэйл бүртгүүлээгүй')
        self.assertContains(response, 'менежерт хандана уу')
        response = self.client.post(reverse('main:password_reset'), {'email': 'nobody@example.com'})
        self.assertContains(response, 'хэрэглэгч олдсонгүй')
        self.assertEqual(len(mail.outbox), 0)

    def test_done_page_shows_masked_email(self):
        profile = make_profile('s11', UserRole.STUDENT, phone='99112233')
        profile.user.email = 'o.bayarjargal10@gmail.com'
        profile.user.save()
        response = self.client.post(reverse('main:password_reset'), {'email': '99112233'}, follow=True)
        self.assertContains(response, 'o.b**********10@gmail.com')
        self.assertNotContains(response, 'o.bayarjargal10@gmail.com')


class MultiSaleTests(TestCase):
    def setUp(self):
        from .models import ChartOfAccounts, Product

        self.manager = make_profile('mgr', UserRole.DIRECTOR, first_name='Менежер')
        self.client.force_login(self.manager.user)
        self.cash = ChartOfAccounts.objects.create(code='100100', name='Касс', account_type='ASSET')
        self.bank = ChartOfAccounts.objects.create(code='110101', name='Хаан', account_type='ASSET')
        ChartOfAccounts.objects.create(code='510101', name='Борлуулалтын орлого', account_type='INCOME')
        self.product = Product.objects.create(
            code='P1', name='Ном', purchase_price=5000, selling_price=10000, initial_stock=10
        )

    def post_sale(self, **extra):
        data = {
            'transaction_date': date.today().isoformat(),  # систем эхлэх огнооноос хойш
            # 1-р мөр устгагдсан, 3-р мөр хоосон — дундах дугаар алгасагдах ёстой
            'product_2': str(self.product.id), 'quantity_2': '3', 'price_2': '10000',
            'product_3': '', 'quantity_3': '1', 'price_3': '',
        }
        data.update(extra)
        return self.client.post(reverse('main:sale_create_multi'), data)

    def test_cash_sale_creates_cash_register_record(self):
        from .models import BankTransaction, Sale

        self.post_sale(payment_method='CASH', cash_account=str(self.cash.id), create_cash_record='1')
        sale = Sale.objects.get()
        self.assertEqual(sale.total_amount, 30000)
        self.assertEqual(sale.salesperson_name, self.manager.full_name)
        tx = BankTransaction.objects.get()
        self.assertEqual((tx.account_type, tx.income_amount, tx.income_type), ('CASH', 30000, 'PRODUCT_SALE'))
        self.assertIsNotNone(tx.accounting_entry)
        self.assertEqual(tx.sale_allocations.get().sale, sale)

    def test_mixed_sale_splits_cash_and_bank(self):
        from .models import AccountingEntry, BankTransaction, Sale

        self.post_sale(payment_method='MIXED', cash_account=str(self.cash.id), bank_account=str(self.bank.id),
                       cash_amount='12000', create_cash_record='1')
        sale = Sale.objects.get()
        self.assertEqual(sale.expected_payment_method, 'Касс + Харилцах')
        self.assertEqual(sale.paid_amount, 30000)
        amounts = dict(AccountingEntry.objects.values_list('debit_account__code', 'debit_amount'))
        self.assertEqual(amounts, {'100100': 12000, '110101': 18000})
        self.assertEqual(BankTransaction.objects.get().income_amount, 12000)

    def test_mixed_sale_rejects_invalid_cash_amount(self):
        from .models import Sale

        self.post_sale(payment_method='MIXED', cash_account=str(self.cash.id), bank_account=str(self.bank.id),
                       cash_amount='30000')
        self.assertFalse(Sale.objects.exists())

    def test_student_customer_becomes_counterparty(self):
        from .models import Sale

        student = make_profile('buyer', UserRole.STUDENT, first_name='Сараа', phone='99001122')
        self.post_sale(payment_method='CASH', cash_account=str(self.cash.id), counterparty=f'p:{student.id}')
        self.assertEqual(Sale.objects.get().customer.profile, student)

    def test_page_renders(self):
        response = self.client.get(reverse('main:sale_create_multi'))
        self.assertContains(response, 'Бэлэн + Данс')
        self.assertContains(response, 'customers-data')


class MultiPurchaseTests(TestCase):
    def setUp(self):
        from .models import ChartOfAccounts, Product

        self.manager = make_profile('pmgr', UserRole.DIRECTOR)
        self.client.force_login(self.manager.user)
        self.cash = ChartOfAccounts.objects.create(code='100100', name='Касс', account_type='ASSET')
        self.bank = ChartOfAccounts.objects.create(code='110101', name='Хаан', account_type='ASSET')
        ChartOfAccounts.objects.create(code='150101', name='Бараа материал', account_type='ASSET')
        ChartOfAccounts.objects.create(code='310101', name='Дансны өглөг', account_type='LIABILITY')
        self.p1 = Product.objects.create(code='P1', name='Ном', purchase_price=5000, selling_price=10000, initial_stock=2)
        self.p2 = Product.objects.create(code='P2', name='Дэвтэр', purchase_price=1000, selling_price=2000, initial_stock=0)

    def post_purchase(self, **extra):
        data = {
            'transaction_date': date.today().isoformat(),
            # 1-р мөр устгагдсан, 4-р мөр хоосон — дундах дугаар алгасагдах ёстой
            'product_2': str(self.p1.id), 'quantity_2': '3', 'price_2': '5000',
            'product_3': str(self.p2.id), 'quantity_3': '10', 'price_3': '1000',
            'product_4': '', 'quantity_4': '1', 'price_4': '',
        }
        data.update(extra)
        return self.client.post(reverse('main:purchase_create_multi'), data)

    def test_cash_purchase_creates_cash_expense_and_stock(self):
        from .models import BankTransaction, StockMovement
        self.post_purchase(payment_method='CASH', cash_account=str(self.cash.id), create_cash_record='1',
                           supplier_name_manual='Шинэ нийлүүлэгч')
        self.assertEqual(StockMovement.objects.filter(movement_type='IN').count(), 2)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.current_stock, 5)
        tx = BankTransaction.objects.get()
        self.assertEqual((tx.account_type, tx.expense_amount, tx.expense_type), ('CASH', 25000, 'PRODUCT_PURCHASE'))
        self.assertEqual((tx.accounting_entry.debit_account.code, tx.accounting_entry.credit_account.code), ('150101', '100100'))
        self.assertEqual(tx.counterparty.counterparty_type, 'SUPPLIER')

    def test_mixed_purchase_splits_and_links_bank_expense(self):
        from .models import AccountingEntry, BankTransaction
        bank_tx = BankTransaction.objects.create(account_type='BANK', bank_account=self.bank, transaction_date=date.today(),
                                                 description='бараа', expense_amount=15000)
        self.post_purchase(payment_method='MIXED', cash_account=str(self.cash.id), bank_account=str(self.bank.id),
                           cash_amount='10000', bank_transaction=str(bank_tx.id), create_cash_record='')
        amounts = dict(AccountingEntry.objects.values_list('credit_account__code', 'credit_amount'))
        self.assertEqual(amounts, {'100100': 10000, '110101': 15000})
        bank_tx.refresh_from_db()
        self.assertTrue(bank_tx.is_processed)
        self.assertEqual((bank_tx.accounting_entry.credit_amount, bank_tx.offset_account.code), (15000, '150101'))
        self.assertEqual(BankTransaction.objects.count(), 1)  # касс бүртгэхгүй сонгосон

    def test_credit_requires_supplier_and_adds_payable(self):
        from .models import StockMovement
        self.post_purchase(payment_method='CREDIT')
        self.assertFalse(StockMovement.objects.exists())

        supplier = Counterparty.objects.create(name='Номын дэлгүүр', counterparty_type='CUSTOMER')
        self.post_purchase(payment_method='CREDIT', counterparty=str(supplier.id))
        supplier.refresh_from_db()
        self.assertEqual((supplier.balance, supplier.counterparty_type), (25000, 'BOTH'))

    def test_invalid_mixed_amount_saves_nothing(self):
        from .models import StockMovement
        self.post_purchase(payment_method='MIXED', cash_account=str(self.cash.id), bank_account=str(self.bank.id),
                           cash_amount='25000')
        self.assertFalse(StockMovement.objects.exists())

    def test_page_renders(self):
        response = self.client.get(reverse('main:purchase_create_multi'))
        self.assertContains(response, 'Бэлэн + Данс')
        self.assertContains(response, 'suppliers-data')
        self.assertContains(response, 'Бараа хувиргалт')
        self.assertNotContains(response, 'POS карт')

    def test_purchase_document_and_list_shows_creator_name(self):
        from .models import Purchase
        self.manager.first_name, self.manager.mongolian_name = 'Сараа', 'Сараа'
        self.manager.save()
        self.post_purchase(payment_method='CASH', cash_account=str(self.cash.id), create_cash_record='1')
        purchase = Purchase.objects.get()
        self.assertEqual((purchase.kind, purchase.total_amount, purchase.stock_movements.count()), ('PURCHASE', 25000, 2))
        self.assertEqual(purchase.accounting_entries.count(), 1)
        page = self.client.get(reverse('main:purchase_list'))
        self.assertEqual(page.context['purchases'][0].creator_name, 'Сараа')
        self.assertContains(page, purchase.purchase_number)

    def test_conversion_consumes_materials_and_sets_cost(self):
        from .models import AccountingEntry, BankTransaction, Product, ProductCategory, Purchase
        material_cat = ProductCategory.objects.get(name='Бэлдэц')  # migration-оор үүссэн
        wax = Product.objects.create(code='M1', name='Лав', purchase_price=300, selling_price=0, initial_stock=100,
                                     category=material_cat)
        wick = Product.objects.create(code='M2', name='Зулай', purchase_price=50, selling_price=0, initial_stock=40)
        candle = Product.objects.create(code='C1', name='Лаа', purchase_price=0, selling_price=5000, initial_stock=0)
        self.client.post(reverse('main:purchase_create_multi'), {
            'transaction_date': date.today().isoformat(), 'payment_method': 'CONVERSION', 'update_cost': '1',
            'product_1': str(candle.id), 'quantity_1': '20', 'price_1': '',
            f'material_{wax.id}': '40', f'material_{wick.id}': '20', f'material_{self.p1.id}': '',
        })
        purchase = Purchase.objects.get()
        self.assertEqual((purchase.kind, purchase.total_amount), ('CONVERSION', 13000))  # 40*300 + 20*50
        candle.refresh_from_db()
        self.assertEqual((candle.current_stock, candle.purchase_price), (20, 650))
        self.assertEqual((wax.current_stock, wick.current_stock), (60, 20))
        self.assertFalse(AccountingEntry.objects.exists())
        self.assertFalse(BankTransaction.objects.exists())
        page = self.client.get(reverse('main:purchase_list'))
        self.assertEqual(page.context['total_amount'], 0)  # хувиргалт худалдан авалтын дүнд орохгүй

        # Бэлдэц хүрэлцэхгүй бол юу ч хадгалахгүй
        self.client.post(reverse('main:purchase_create_multi'), {
            'transaction_date': date.today().isoformat(), 'payment_method': 'CONVERSION',
            'product_1': str(candle.id), 'quantity_1': '5', f'material_{wax.id}': '999',
        })
        self.assertEqual(Purchase.objects.count(), 1)

    def test_edit_rebuilds_purchase_and_relinks_bank(self):
        from .models import AccountingEntry, BankTransaction, Purchase
        bank_tx = BankTransaction.objects.create(account_type='BANK', bank_account=self.bank, transaction_date=date.today(),
                                                 description='бараа', expense_amount=25000)
        self.post_purchase(payment_method='BANK', bank_account=str(self.bank.id), bank_transaction=str(bank_tx.id))
        purchase = Purchase.objects.get()
        first_in = purchase.stock_movements.order_by('id').first()
        edit_url = reverse('main:purchase_edit', args=[first_in.id])

        page = self.client.get(edit_url)
        self.assertEqual(page.context['edit_data']['bank_transaction'], bank_tx.id)
        self.assertEqual(len(page.context['edit_data']['items']), 2)

        # Нэг бараа хасаж, бэлэн + данс болгоно
        self.client.post(edit_url, {
            'transaction_date': date.today().isoformat(), 'payment_method': 'MIXED',
            'product_1': str(self.p1.id), 'quantity_1': '5', 'price_1': '5000',
            'cash_account': str(self.cash.id), 'bank_account': str(self.bank.id), 'cash_amount': '10000',
            'bank_transaction': str(bank_tx.id), 'create_cash_record': '1',
        })
        purchase.refresh_from_db()
        self.assertEqual((purchase.total_amount, purchase.payment_method, purchase.stock_movements.count()), (25000, 'MIXED', 1))
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual((self.p1.current_stock, self.p2.current_stock), (7, 0))
        amounts = dict(AccountingEntry.objects.values_list('credit_account__code', 'credit_amount'))
        self.assertEqual(amounts, {'100100': 10000, '110101': 15000})
        bank_tx.refresh_from_db()
        self.assertEqual(bank_tx.accounting_entry.related_purchase, purchase)
        self.assertEqual(BankTransaction.objects.filter(account_type='CASH').get().expense_amount, 10000)

        # Устгахад бүгд буцна, банкны гүйлгээ үлдэж холбоогүй болно
        self.client.post(reverse('main:purchase_delete', args=[purchase.stock_movements.first().id]))
        self.assertFalse(Purchase.objects.exists())
        self.assertFalse(AccountingEntry.objects.exists())
        bank_tx.refresh_from_db()
        self.assertIsNone(bank_tx.accounting_entry)
        self.assertFalse(BankTransaction.objects.filter(account_type='CASH').exists())
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.current_stock, 2)

    def test_edit_credit_reverses_payable(self):
        from .models import Purchase
        supplier = Counterparty.objects.create(name='Нийлүүлэгч', counterparty_type='SUPPLIER')
        self.post_purchase(payment_method='CREDIT', counterparty=str(supplier.id))
        movement = Purchase.objects.get().stock_movements.first()
        self.client.post(reverse('main:purchase_edit', args=[movement.id]), {
            'transaction_date': date.today().isoformat(), 'payment_method': 'CREDIT', 'counterparty': str(supplier.id),
            'product_1': str(self.p1.id), 'quantity_1': '1', 'price_1': '5000',
        })
        supplier.refresh_from_db()
        self.assertEqual(supplier.balance, 5000)

    def test_link_bank_expense_to_bank_purchase_from_link_page(self):
        from .models import AccountingEntry, BankTransaction, Purchase
        self.post_purchase(payment_method='BANK', bank_account=str(self.bank.id))
        purchase = Purchase.objects.get()
        bank_tx = BankTransaction.objects.create(account_type='BANK', bank_account=self.bank, transaction_date=date.today(),
                                                 description='бараа', expense_amount=25000)
        url = reverse('main:link_bank_transaction_to_journal', args=[bank_tx.id])
        page = self.client.get(url)
        self.assertEqual([p.id for p in page.context['purchase_candidates']], [purchase.id])
        self.assertEqual(page.context['link_data']['initial_mode'], 'purchase')

        self.client.post(url, {'link_purchase': str(purchase.id)})
        bank_tx.refresh_from_db()
        self.assertEqual(bank_tx.accounting_entry.related_purchase, purchase)
        self.assertEqual((bank_tx.offset_account.code, bank_tx.expense_type), ('150101', 'PRODUCT_PURCHASE'))

        # Журнал цуцлахад худалдан авалтын журнал үлдэж, гүйлгээ л салгагдана
        self.client.post(url, {'unlink_type': 'journal'})
        bank_tx.refresh_from_db()
        self.assertIsNone(bank_tx.accounting_entry)
        self.assertEqual(AccountingEntry.objects.filter(related_purchase=purchase).count(), 1)

    def test_bank_expense_pays_credit_purchase_and_unlink_reverts(self):
        from .models import AccountingEntry, BankTransaction, Purchase
        supplier = Counterparty.objects.create(name='Нийлүүлэгч', counterparty_type='SUPPLIER')
        self.post_purchase(payment_method='CREDIT', counterparty=str(supplier.id))
        purchase = Purchase.objects.get()
        bank_tx = BankTransaction.objects.create(account_type='BANK', bank_account=self.bank, transaction_date=date.today(),
                                                 description='өглөг', expense_amount=10000)
        url = reverse('main:link_bank_transaction_to_journal', args=[bank_tx.id])
        self.client.post(url, {'link_purchase': str(purchase.id)})
        purchase.refresh_from_db()
        supplier.refresh_from_db()
        bank_tx.refresh_from_db()
        self.assertEqual((purchase.paid_amount, purchase.status, supplier.balance), (10000, 'RECEIVED', 15000))
        entry = bank_tx.accounting_entry
        self.assertEqual((entry.debit_account.code, entry.credit_account.code, entry.related_purchase), ('310101', '110101', purchase))

        # Үлдэгдлээс их дүнтэй гүйлгээ холбогдохгүй
        big_tx = BankTransaction.objects.create(account_type='BANK', bank_account=self.bank, transaction_date=date.today(),
                                                description='их', expense_amount=20000)
        self.client.post(reverse('main:link_bank_transaction_to_journal', args=[big_tx.id]), {'link_purchase': str(purchase.id)})
        big_tx.refresh_from_db()
        self.assertIsNone(big_tx.accounting_entry)

        self.client.post(url, {'unlink_type': 'all'})
        purchase.refresh_from_db()
        supplier.refresh_from_db()
        self.assertEqual((purchase.paid_amount, supplier.balance), (0, 25000))
        self.assertFalse(AccountingEntry.objects.filter(debit_account__code='310101').exists())

    def test_create_purchase_from_bank_transaction_in_embed(self):
        from .models import BankTransaction, Purchase
        supplier = Counterparty.objects.create(name='Нийлүүлэгч', counterparty_type='SUPPLIER')
        bank_tx = BankTransaction.objects.create(account_type='BANK', bank_account=self.bank, transaction_date=date.today(),
                                                 description='бараа авсан', expense_amount=25000, counterparty=supplier)
        link_page = self.client.get(reverse('main:link_bank_transaction_to_journal', args=[bank_tx.id]))
        self.assertTrue(link_page.context['can_create_purchase'])
        self.assertContains(link_page, 'purchaseFrame')

        url = reverse('main:purchase_create_multi') + f'?embed=1&bank_tx={bank_tx.id}'
        page = self.client.get(url)
        self.assertEqual(page['X-Frame-Options'], 'SAMEORIGIN')
        self.assertTemplateUsed(page, 'main/base_embed.html')
        prefill = page.context['prefill_data']
        self.assertEqual((prefill['tx'], prefill['payment_method'], prefill['account'], prefill['supplier']['id']),
                         (bank_tx.id, 'BANK', self.bank.id, str(supplier.id)))
        self.assertIn(bank_tx.id, [t['id'] for t in page.context['transactions_data']])

        response = self.post_purchase_to(url, payment_method='BANK', bank_account=str(self.bank.id),
                                         bank_transaction=str(bank_tx.id), counterparty=str(supplier.id))
        self.assertTemplateUsed(response, 'main/embed_done.html')
        bank_tx.refresh_from_db()
        self.assertEqual(bank_tx.accounting_entry.related_purchase, Purchase.objects.get())

    def test_entered_line_total_is_kept_and_unit_price_derived(self):
        from decimal import Decimal
        from .models import AccountingEntry, Purchase
        self.client.post(reverse('main:purchase_create_multi'), {
            'transaction_date': date.today().isoformat(), 'payment_method': 'BANK', 'bank_account': str(self.bank.id),
            'product_1': str(self.p1.id), 'quantity_1': '3', 'price_1': '3333.33', 'total_1': '10000',
            'product_2': str(self.p2.id), 'quantity_2': '2', 'price_2': '1500', 'total_2': '',
        })
        purchase = Purchase.objects.get()
        self.assertEqual(purchase.total_amount, 13000)
        m1 = purchase.stock_movements.get(product=self.p1)
        self.assertEqual((m1.price, m1.total_amount), (Decimal('3333.33'), 10000))
        self.assertEqual(purchase.stock_movements.get(product=self.p2).total_amount, 3000)
        self.assertEqual(AccountingEntry.objects.get().debit_amount, 13000)

        page = self.client.get(reverse('main:purchase_edit', args=[m1.id]))
        self.assertEqual(page.context['edit_data']['items'][0]['total'], 10000)

    def post_purchase_to(self, url, **extra):
        data = {
            'transaction_date': date.today().isoformat(),
            'product_1': str(self.p1.id), 'quantity_1': '3', 'price_1': '5000',
            'product_2': str(self.p2.id), 'quantity_2': '10', 'price_2': '1000',
        }
        data.update(extra)
        return self.client.post(url, data)

    def test_legacy_movements_grouped_into_document(self):
        from .models import AccountingEntry, Purchase, StockMovement
        entry = AccountingEntry.objects.create(entry_number='PUR-OLD-1', entry_date=date.today(), description='хуучин',
                                               debit_account=self.cash, credit_account=self.cash,
                                               debit_amount=25000, credit_amount=25000)
        m1 = StockMovement.objects.create(product=self.p1, movement_type='IN', quantity=3, price=5000,
                                          payment_method='CASH', created_by=self.manager.user, accounting_entry=entry)
        StockMovement.objects.create(product=self.p2, movement_type='IN', quantity=10, price=1000,
                                     payment_method='CASH', created_by=self.manager.user)
        page = self.client.get(reverse('main:purchase_edit', args=[m1.id]))
        purchase = Purchase.objects.get()
        self.assertEqual((purchase.stock_movements.count(), purchase.total_amount), (2, 25000))
        self.assertEqual(entry.__class__.objects.get(id=entry.id).related_purchase, purchase)
        self.assertEqual(page.context['edit_data']['cash_account'], self.cash.id)

    def test_category_create_endpoint(self):
        import json
        from .models import ProductCategory
        url = reverse('main:product_category_create')
        data = self.client.post(url, json.dumps({'name': 'Сав баглаа'}), content_type='application/json').json()
        self.assertTrue(data['success'] and data['created'])
        again = self.client.post(url, json.dumps({'name': 'сав баглаа'}), content_type='application/json').json()
        self.assertEqual((again['id'], again['created']), (data['id'], False))
        self.assertEqual(sum(c.name.lower() == 'сав баглаа' for c in ProductCategory.objects.all()), 1)


class ChartAccountCreateTests(TestCase):
    def test_superuser_can_create_account(self):
        from .models import ChartOfAccounts

        admin = make_profile('root', UserRole.DIRECTOR)
        admin.user.is_superuser = True
        admin.user.save()
        self.client.force_login(admin.user)
        self.assertContains(self.client.get(reverse('main:chart_of_accounts_list')), 'Шинэ данс')
        self.client.post(reverse('main:chart_account_create'),
                         {'code': '110102', 'name': 'Голомт', 'account_type': 'ASSET'})
        self.assertTrue(ChartOfAccounts.objects.filter(code='110102').exists())

    def test_director_still_cannot_create_account(self):
        from .models import ChartOfAccounts

        self.client.force_login(make_profile('dir', UserRole.DIRECTOR).user)
        self.client.post(reverse('main:chart_account_create'),
                         {'code': '110103', 'name': 'ХХБ', 'account_type': 'ASSET'})
        self.assertFalse(ChartOfAccounts.objects.filter(code='110103').exists())


def make_xac_statement(path, rows, opening='1,000,000.00'):
    """Хас банкны хуулгатай ижил бүтэцтэй xlsx үүсгэх"""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([None, None, None, 'ДАНСНЫ ХУУЛГА', None, None, None])
    ws.append(['.', None, None, None, None, None, None])
    ws.append(['Үндсэн эзэмшигч:', 'ТЕСТ', None, None, None, 'Нийт орлого:', '0'])
    ws.append(['Хамтран эзэмшигч:', '-', None, None, None, 'Нийт зарлага:', '0'])
    ws.append(['Дансны дугаар:', '5006157789', None, None, None, None, None])
    ws.append(['Бүтээгдэхүүн:', 'ХАРИЛЦАХ ДАНС', None, None, None, 'Эхлэх:', '2026-05-01'])
    ws.append(['Валют:', 'MNT', None, None, None, 'Дуусах:', '2026-05-31'])
    ws.append([None, '.', None, None, None, None, None])
    ws.append(['Огноо', 'Гүйлгээний утга', 'Харьцсан данс', 'Гүйлгээний дугаар', 'Орлого', 'Зарлага', 'Үлдэгдэл'])
    ws.append(['2026-05-01', 'Эхний үлдэгдэл', None, None, None, None, opening])
    for r in rows:
        ws.append(list(r))
    ws.append([rows[-1][0], 'Эцсийн үлдэгдэл', None, None, None, None, rows[-1][6]])
    ws.append([None, None, None, None, None, 'Хэвлэсэн:', 'Хасбанк'])
    wb.save(path)


XAC_ROWS = [
    # Шилжүүлэг ба шимтгэл ижил гүйлгээний дугаартай
    ('2026-05-03', 'Шилжүүлэг   ', 'БОЛОР БАТСҮРЭН ХААН БАНК-5039139089', 'SX1', '-', '100,000.00', '900,000.00'),
    ('2026-05-03', 'Банк хоорондын шилжүүлгийн шимтгэл', 'Банк хоорондын шилжүүлгийн шимтгэл-5006157789', 'SX1', '-', '200.00', '899,800.00'),
    # Нэг өдөр ижил утга, ижил дүнтэй хоёр шимтгэл (өөр дугаартай)
    ('2026-05-14', 'Банк хоорондын шилжүүлгийн шимтгэл', 'Банк хоорондын шилжүүлгийн шимтгэл-5006157789', 'SX2', '-', '200.00', '899,600.00'),
    ('2026-05-14', 'Банк хоорондын шилжүүлгийн шимтгэл', 'Банк хоорондын шилжүүлгийн шимтгэл-5006157789', 'SX3', '-', '200.00', '899,400.00'),
    ('2026-05-20', 'СЕТТЛЕМЕНТ ХААВ', 'GOTOPA, 44311091-100260418315', 'XB9', '40,000.00', '-', '939,400.00'),
]


class XacBankImportTests(TestCase):
    def setUp(self):
        import tempfile
        from .models import ChartOfAccounts

        self.tmpdir = tempfile.mkdtemp()
        self.account = ChartOfAccounts.objects.create(code='110103', name='Хас банк', account_type='ASSET')

    def run_import(self, rows, name='a.xlsx', account=None):
        import os
        from .import_bank_transactions import import_bank_transactions

        path = os.path.join(self.tmpdir, name)
        make_xac_statement(path, rows)
        return import_bank_transactions(path, account or self.account)

    def test_imports_all_rows_including_same_day_identical_fees(self):
        from .models import BankTransaction

        result = self.run_import(XAC_ROWS)
        self.assertEqual((result['created'], result['skipped']), (5, 0))
        self.assertEqual(result['statement_account'], '5006157789')
        self.assertEqual(result['warnings'], [])
        self.assertEqual(BankTransaction.objects.filter(reference_number='SX1').count(), 2)
        self.assertEqual(BankTransaction.objects.filter(transaction_date='2026-05-14', expense_amount=200).count(), 2)
        income = BankTransaction.objects.get(reference_number='XB9')
        self.assertEqual((income.bank_name, income.income_amount, income.counterparty_account),
                         ('XAC', 40000, '100260418315'))
        self.assertEqual(income.counterparty_name, 'GOTOPA, 44311091')

    def test_reimport_same_file_creates_nothing(self):
        from .models import BankTransaction

        self.run_import(XAC_ROWS)
        result = self.run_import(XAC_ROWS)
        self.assertEqual((result['created'], result['skipped']), (0, 5))
        self.assertEqual(BankTransaction.objects.count(), 5)

    def test_overlapping_statement_only_adds_new_rows(self):
        from .models import BankTransaction

        self.run_import(XAC_ROWS[:3])
        result = self.run_import(XAC_ROWS[2:], name='b.xlsx')
        self.assertEqual((result['created'], result['skipped']), (2, 1))
        self.assertEqual(BankTransaction.objects.count(), 5)

    def test_reimport_with_same_day_rows_reordered_creates_nothing(self):
        """Цаггүй тул банк нэг өдрийн мөрүүдийг өөр дарааллаар (өөр үлдэгдэлтэй) гаргадаг."""
        from .models import BankTransaction

        self.run_import(XAC_ROWS)
        reordered = [
            XAC_ROWS[1][:6] + ('999,800.00',), XAC_ROWS[0][:6] + ('899,800.00',),  # шимтгэл түрүүлж
            XAC_ROWS[3], XAC_ROWS[2], XAC_ROWS[4],
        ]
        result = self.run_import(reordered, name='b.xlsx')
        self.assertEqual((result['created'], result['skipped']), (0, 5))
        self.assertEqual(BankTransaction.objects.count(), 5)

    def test_dedupe_removes_earlier_duplicates_keeping_linked_copy(self):
        from .bank_dedup import find_duplicates, remove_duplicate
        from .models import AccountingEntry, BankTransaction, ChartOfAccounts

        self.run_import(XAC_ROWS)
        # Хуучин (засахаас өмнөх) импортын давхардлыг дуурайх: өөр үлдэгдэлтэй, өөр импорт
        original = BankTransaction.objects.get(reference_number='SX1', expense_amount=200)
        dup = BankTransaction.objects.get(pk=original.pk)
        dup.pk = None
        dup.closing_balance = 999800
        dup.save()
        BankTransaction.objects.filter(pk=dup.pk).update(imported_at=original.imported_at.replace(year=2025))
        fee_acc = ChartOfAccounts.objects.create(code='702701', name='Шимтгэл', account_type='EXPENSE')
        entry = AccountingEntry.objects.create(
            entry_number='F1', entry_date=dup.transaction_date, debit_account=fee_acc, credit_account=self.account,
            debit_amount=200, credit_amount=200, description='шимтгэл')
        BankTransaction.objects.filter(pk=dup.pk).update(accounting_entry=entry)

        groups = find_duplicates()
        self.assertEqual(len(groups), 1)
        self.assertEqual([t.id for t in groups[0]['keep']], [dup.pk])       # журналтай нь үлдэнэ
        self.assertEqual([t.id for t in groups[0]['remove']], [original.pk])
        self.assertEqual(remove_duplicate(groups[0]['remove'][0]), [])
        self.assertEqual(BankTransaction.objects.count(), 5)
        self.assertEqual(find_duplicates(), [])

    def test_dedupe_keeps_genuine_same_key_rows_from_one_import(self):
        from .bank_dedup import find_duplicates
        rows = list(XAC_ROWS)
        rows.insert(2, ('2026-05-03', 'Банк хоорондын шилжүүлгийн шимтгэл', 'x-5006157789', 'SX1', '-', '200.00', '899,600.00'))
        self.run_import(rows)
        self.assertEqual(find_duplicates(), [])

    def test_same_statement_into_other_account_is_blocked_with_warning(self):
        from .models import BankTransaction, ChartOfAccounts

        self.run_import(XAC_ROWS)
        other = ChartOfAccounts.objects.create(code='110104', name='Өөр данс', account_type='ASSET')
        result = self.run_import(XAC_ROWS, account=other)
        self.assertEqual(result['created'], 0)
        self.assertIn('өөр дансанд', result['warnings'][0])
        self.assertEqual(BankTransaction.objects.count(), 5)

    def test_balance_mismatch_is_reported(self):
        rows = list(XAC_ROWS)
        rows[1] = rows[1][:6] + ('111.00',)
        result = self.run_import(rows)
        self.assertTrue(any('үлдэгдэл таарахгүй' in w for w in result['warnings']))

    def test_bad_amount_aborts_whole_file(self):
        from .import_bank_transactions import BankImportError
        from .models import BankTransaction

        rows = list(XAC_ROWS)
        rows[2] = rows[2][:5] + ('abc',) + rows[2][6:]
        with self.assertRaises(BankImportError):
            self.run_import(rows)
        self.assertEqual(BankTransaction.objects.count(), 0)


class KhanGolomtDuplicateTests(TestCase):
    GOLOMT_HEADER = ['Гүйлгээний огноо', 'Гүйлгээний утга', 'Харьцсан дансны нэр', 'Харьцсан данс', 'Ханш', 'Орлого', 'Зарлага']
    KHAN_HEADER = ['Гүйлгээний огноо', 'Салбар', 'Эхний үлдэгдэл', 'Дебит гүйлгээ', 'Кредит гүйлгээ',
                   'Эцсийн үлдэгдэл', 'Гүйлгээний утга', 'Харьцсан данс']
    FEE = ['2026-05-14', 'Шимтгэл', 'Голомт', '123', 1, None, 200]
    GOLOMT_ROWS = [
        FEE,
        FEE,  # Нэг өдөр ижил утга, ижил дүнтэй хоёр дахь жинхэнэ шимтгэл
        ['2026-05-15', 'Орлого', 'Бат', '456', 1, 50000, None],
    ]
    KHAN_ROWS = [
        ['2026-05-14T10:00', '5000', 100000, -200, 0, 99800, 'Шимтгэл', 'Хаан'],
        ['2026-05-14T10:00', '5000', 99800, -200, 0, 99600, 'Шимтгэл', 'Хаан'],
    ]

    def setUp(self):
        import tempfile
        from .models import ChartOfAccounts

        self.tmpdir = tempfile.mkdtemp()
        self.account = ChartOfAccounts.objects.create(code='110101', name='Банк', account_type='ASSET')

    def run_import(self, header, rows, name):
        import os
        import openpyxl
        from .import_bank_transactions import import_bank_transactions

        path = os.path.join(self.tmpdir, name)
        wb = openpyxl.Workbook()
        wb.active.append(header)
        for row in rows:
            wb.active.append(row)
        wb.save(path)
        return import_bank_transactions(path, self.account)

    def test_golomt_keeps_identical_same_day_rows_and_reimport_is_idempotent(self):
        from .models import BankTransaction

        result = self.run_import(self.GOLOMT_HEADER, self.GOLOMT_ROWS, 'g1.xlsx')
        self.assertEqual(result['created'], 3)
        self.assertEqual(BankTransaction.objects.filter(expense_amount=200).count(), 2)

        result = self.run_import(self.GOLOMT_HEADER, self.GOLOMT_ROWS, 'g2.xlsx')
        self.assertEqual((result['created'], result['skipped']), (0, 3))
        self.assertEqual(BankTransaction.objects.count(), 3)

    def test_golomt_reimport_recovers_row_lost_by_old_import(self):
        from .models import BankTransaction

        # Хуучин логикоор 2 шимтгэлээс зөвхөн 1 нь орсон байсан гэж үзье
        self.run_import(self.GOLOMT_HEADER, [self.FEE], 'old.xlsx')
        result = self.run_import(self.GOLOMT_HEADER, self.GOLOMT_ROWS, 'full.xlsx')
        self.assertEqual((result['created'], result['skipped']), (2, 1))
        self.assertEqual(BankTransaction.objects.filter(expense_amount=200).count(), 2)

    def test_khan_same_time_same_amount_rows_distinguished_by_balance(self):
        from .models import BankTransaction

        result = self.run_import(self.KHAN_HEADER, self.KHAN_ROWS, 'k1.xlsx')
        self.assertEqual(result['created'], 2)
        result = self.run_import(self.KHAN_HEADER, self.KHAN_ROWS, 'k2.xlsx')
        self.assertEqual((result['created'], result['skipped']), (0, 2))
        self.assertEqual(BankTransaction.objects.count(), 2)

    def test_khan_reimport_with_different_time_same_balance_creates_nothing(self):
        """Хаан банк сарын хураамжийн цагийг хуулга бүрт өөрөөр гаргадаг (09:54 / 06:30)."""
        from .models import BankTransaction

        self.run_import(self.KHAN_HEADER, self.KHAN_ROWS, 'k1.xlsx')
        shifted = [['2026-05-14T06:30'] + row[1:] for row in self.KHAN_ROWS]
        result = self.run_import(self.KHAN_HEADER, shifted, 'k2.xlsx')
        self.assertEqual((result['created'], result['skipped']), (0, 2))
        self.assertEqual(BankTransaction.objects.count(), 2)


class BooksPeriodTests(TestCase):
    """Систем эхлэх огноо: архивын гүйлгээ нуугдах, superuser-д л харагдах, үлдэгдэлд нөлөөлөхгүй."""

    def setUp(self):
        from decimal import Decimal
        from .models import BankTransaction, ChartOfAccounts, FinanceSettings
        from .books_period import clear_start_date_cache
        settings_obj, _ = FinanceSettings.objects.get_or_create(pk=1)
        settings_obj.books_start_date = date(2026, 9, 30)
        settings_obj.save()
        clear_start_date_cache()

        self.bank = ChartOfAccounts.objects.create(code='110199', name='Тест банк', account_type='ASSET')
        self.income = ChartOfAccounts.objects.create(code='510199', name='Тест орлого', account_type='INCOME')
        self.old_tx = BankTransaction.objects.create(
            account_type='BANK', bank_account=self.bank, transaction_date=date(2026, 9, 1),
            description='Хуучин төлбөр', income_amount=Decimal('50000'),
        )
        self.new_tx = BankTransaction.objects.create(
            account_type='BANK', bank_account=self.bank, transaction_date=date(2026, 10, 2),
            description='Шинэ төлбөр', income_amount=Decimal('70000'),
        )
        self.accountant = make_profile('nyagtlan', UserRole.ACCOUNTANT)
        self.superuser = make_profile('root', UserRole.DIRECTOR)
        self.superuser.user.is_superuser = True
        self.superuser.user.save()

    def ids_in_list(self, user, **params):
        self.client.force_login(user)
        response = self.client.get(reverse('main:bank_transaction_list'), params)
        self.assertEqual(response.status_code, 200)
        return {tx.id for tx in response.context['transactions']}

    def test_old_transactions_hidden_from_list(self):
        self.assertEqual(self.ids_in_list(self.accountant.user), {self.new_tx.id})

    def test_archive_only_for_superuser(self):
        self.assertEqual(self.ids_in_list(self.superuser.user, archive='1'), {self.old_tx.id})
        # superuser биш хэрэглэгчид ?archive=1 нөлөөлөхгүй
        self.assertEqual(self.ids_in_list(self.accountant.user, archive='1'), {self.new_tx.id})

    def test_archived_link_page_denied_for_non_superuser(self):
        self.client.force_login(self.accountant.user)
        url = reverse('main:link_bank_transaction_to_journal', args=[self.old_tx.id])
        self.assertRedirects(self.client.get(url), reverse('main:bank_transaction_list'), fetch_redirect_response=False)
        self.client.force_login(self.superuser.user)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_archived_journal_entry_does_not_change_balances(self):
        from decimal import Decimal
        from .models import AccountingEntry
        AccountingEntry.objects.create(
            entry_date=date(2026, 9, 1), entry_number='OLD-1', description='Хуучин',
            debit_account=self.bank, debit_amount=Decimal('50000'),
            credit_account=self.income, credit_amount=Decimal('50000'),
        )
        new_entry = AccountingEntry.objects.create(
            entry_date=date(2026, 10, 2), entry_number='NEW-1', description='Шинэ',
            debit_account=self.bank, debit_amount=Decimal('70000'),
            credit_account=self.income, credit_amount=Decimal('70000'),
        )
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.debit_balance, Decimal('70000'))
        new_entry.delete()
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.debit_balance, Decimal('0'))

    def test_old_dated_journal_rejected_for_non_superuser(self):
        from .models import AccountingEntry
        self.client.force_login(self.accountant.user)
        self.client.post(reverse('main:journal_create'), {
            'entry_number': 'X-1', 'entry_date': '2026-09-01', 'debit_account': self.bank.id,
            'credit_account': self.income.id, 'amount': '1000', 'description': 'хуучин огноо',
        })
        self.assertFalse(AccountingEntry.objects.filter(entry_number='X-1').exists())


class PosSettlementTests(TestCase):
    """POS борлуулалт → ХАС банкны "СЕТТЛЕМЕНТ ХААВ"-тай тулгах."""

    def setUp(self):
        from datetime import timedelta
        from .models import ChartOfAccounts, CashFlowIndicator, Product

        self.manager = make_profile('posmgr', UserRole.DIRECTOR)
        self.client.force_login(self.manager.user)
        self.xac = ChartOfAccounts.objects.create(code='110103', name='ХАС БАНК', account_type='ASSET')
        ChartOfAccounts.objects.create(code='510101', name='Борлуулалтын орлого', account_type='INCOME')
        ChartOfAccounts.objects.create(code='702701', name='Банкны шимтгэлийн зардал', account_type='EXPENSE')
        CashFlowIndicator.objects.create(code='1.1.1', name='Борлуулалт', flow_type='INCOME')
        CashFlowIndicator.objects.create(code='1.2.9', name='Бусад зарлага', flow_type='EXPENSE')
        self.product = Product.objects.create(code='P1', name='Ном', purchase_price=5000, selling_price=10000, initial_stock=10)
        self.sale_day = date.today()
        self.statement_day = self.sale_day + timedelta(days=1)

    def post_pos_sale(self, qty='2'):
        return self.client.post(reverse('main:sale_create_multi'), {
            'transaction_date': self.sale_day.isoformat(), 'payment_method': 'POS',
            'pos_bank_account': str(self.xac.id),
            'product_1': str(self.product.id), 'quantity_1': qty, 'price_1': '10000',
        })

    def add_statement(self, amount, fee):
        from .models import BankTransaction
        prefix = f'{self.sale_day:%Y.%m.%d}, 187, 44311091'
        settlement = BankTransaction.objects.create(
            account_type='BANK', bank_account=self.xac, transaction_date=self.statement_day,
            description=f'{prefix} СЕТТЛЕМЕНТ ХААВ', income_amount=amount)
        fee_tx = BankTransaction.objects.create(
            account_type='BANK', bank_account=self.xac, transaction_date=self.statement_day,
            description=f'{prefix} СЕТТЛЕМЕНТИЙН ШИМТГЭЛ СУУТГАВ', expense_amount=fee)
        return settlement, fee_tx

    def test_pos_sale_waits_for_settlement(self):
        from .models import AccountingEntry, Sale
        self.post_pos_sale()
        sale = Sale.objects.get()
        self.assertEqual((sale.pos_bank_account, sale.expected_payment_method, sale.status, sale.paid_amount),
                         (self.xac, 'POS', 'DRAFT', 0))
        # Орлогын журнал сэттлмэнт холбох хүртэл бичигдэхгүй
        self.assertFalse(AccountingEntry.objects.filter(credit_account__code='510101').exists())

    def test_settlement_links_many_sales(self):
        """Банкны гүйлгээ → "Олон борлуулалттай холбох": тухайн өдрийн POS борлуулалт урьдчилан сонгогдоно."""
        from .models import AccountingEntry, Sale
        self.post_pos_sale(qty='1')
        self.post_pos_sale(qty='3')
        settlement, _ = self.add_statement(40000, 400)
        link_page = reverse('main:link_bank_transaction_to_journal', args=[settlement.id])
        page = self.client.get(link_page)
        self.assertEqual(page.context['multi_sale_day'], self.sale_day)
        rows = page.context['multi_sale_rows']
        self.assertEqual([(r['checked'], r['is_pos_day']) for r in rows], [(True, True), (True, True)])

        data = {'sale_ids': [str(r['sale'].id) for r in rows]}
        data.update({f"amount_{r['sale'].id}": str(r['amount']) for r in rows})
        self.client.post(reverse('main:bank_transaction_link_sales', args=[settlement.id]), data)
        settlement.refresh_from_db()
        self.assertEqual(settlement.sale_allocations.count(), 2)
        self.assertTrue(settlement.is_processed)
        self.assertEqual(list(Sale.objects.values_list('status', flat=True)), ['PAID', 'PAID'])
        entry = settlement.accounting_entry
        self.assertEqual((entry.debit_account.code, entry.credit_account.code, entry.debit_amount), ('110103', '510101', 40000))

        # Бүгдийг сонгохгүй илгээвэл холболт цуцлагдана
        self.client.post(reverse('main:bank_transaction_link_sales', args=[settlement.id]), {})
        settlement.refresh_from_db()
        self.assertFalse(settlement.sale_allocations.exists() or settlement.is_processed)
        self.assertEqual(list(Sale.objects.values_list('status', flat=True)), ['DRAFT', 'DRAFT'])
        self.assertFalse(AccountingEntry.objects.filter(credit_account__code='510101').exists())

    def test_partially_linked_settlement_shows_all_sales_and_guards_old_form(self):
        """1,152,000-аас 152,000-г 3 борлуулалтад холбосон үед эхнийх нь л тооцогдож 1,085,000 гэж харагдаж байсан."""
        from .models import Sale
        self.post_pos_sale(qty='1')
        self.post_pos_sale(qty='3')
        settlement, _ = self.add_statement(100000, 1000)
        sales = list(Sale.objects.order_by('id'))
        data = {'sale_ids': [str(x.id) for x in sales]}
        data.update({f'amount_{x.id}': str(x.total_amount) for x in sales})
        self.client.post(reverse('main:bank_transaction_link_sales', args=[settlement.id]), data)

        link_page = reverse('main:link_bank_transaction_to_journal', args=[settlement.id])
        page = self.client.get(link_page)
        self.assertIsNone(page.context['existing_sale_allocation'])
        self.assertEqual(len(page.context['sale_allocations_all']), 2)
        self.assertEqual(page.context['sale_alloc_left'], 60000)
        self.assertContains(page, 'Холбогдоогүй үлдэгдэл 60,000₮')

        # Банкны гүйлгээний жагсаалтын "Төлөв" баганад хүлээгдэж буй дүн
        listing = self.client.get(reverse('main:bank_transaction_list'))
        row = next(t for t in listing.context['transactions'] if t.id == settlement.id)
        self.assertEqual((row.pending_amount, row.linked_amount), (60000, 40000))
        self.assertContains(listing, '40,000₮ холбогдсон')

        # Нэг борлуулалтын хуучин формоор хадгалахад бусад борлуулалтын холболт устах ёсгүй
        self.client.post(link_page, {'offset_account': str(self.xac.id), 'income_type': 'PRODUCT_SALE', 'sale': str(sales[0].id)})
        self.assertEqual(settlement.sale_allocations.count(), 2)
        self.assertEqual(page.context['link_data']['fixed_sale_amount'], 40000)

    def make_student(self):
        from .models import ChartOfAccounts, Enrollment
        tuition = ChartOfAccounts.objects.create(code='510102', name='Сургалтын төлбөрийн орлого', account_type='INCOME')
        student = make_profile('posstudent', UserRole.STUDENT)
        course = make_course()
        Enrollment.objects.create(student=student, course=course, status='APPROVED')
        return tuition, student, course

    def test_settlement_split_between_sales_and_student_payment(self):
        """Сэттлмэнтийн 40,000-г 2 борлуулалтад, үлдсэн 60,000-г сурагчийн төлбөрт — журнал хоёр дансанд."""
        from .models import AccountingEntry, Sale
        tuition, student, course = self.make_student()
        self.post_pos_sale(qty='1')
        self.post_pos_sale(qty='3')
        settlement, _ = self.add_statement(100000, 1000)
        sales = list(Sale.objects.order_by('id'))
        data = {'sale_ids': [str(x.id) for x in sales]}
        data.update({f'amount_{x.id}': str(x.total_amount) for x in sales})
        self.client.post(reverse('main:bank_transaction_link_sales', args=[settlement.id]), data)

        link_page = reverse('main:link_bank_transaction_to_journal', args=[settlement.id])
        self.client.post(link_page, {
            'offset_account': str(tuition.id), 'income_type': 'STUDENT_PAYMENT',
            'allocations[0][student]': str(student.id), 'allocations[0][course]': str(course.id),
            'allocations[0][month_year]': '2026-10', 'allocations[0][amount]': '60000',
        })
        settlement.refresh_from_db()
        self.assertEqual(settlement.sale_allocations.count(), 2)  # борлуулалтын холболт хэвээр
        self.assertEqual(list(settlement.allocations.values_list('amount', flat=True)), [60000])
        main, sale_part = settlement.accounting_entry, settlement.sale_revenue_entry
        self.assertEqual((main.debit_account.code, main.credit_account.code, main.debit_amount), ('110103', '510102', 60000))
        self.assertEqual((sale_part.debit_account.code, sale_part.credit_account.code, sale_part.debit_amount), ('110103', '510101', 40000))
        self.assertTrue(settlement.is_processed)
        self.assertEqual(set(Sale.objects.values_list('status', flat=True)), {'PAID'})

        # Олон борлуулалтын хэсгээр нэгийг хасахад — сурагчийн хэсэг хэвээр, борлуулалтын бичилт шинэчлэгдэнэ
        keep = sales[1]
        self.client.post(reverse('main:bank_transaction_link_sales', args=[settlement.id]),
                         {'sale_ids': [str(keep.id)], f'amount_{keep.id}': str(keep.total_amount)})
        settlement.refresh_from_db()
        self.assertEqual((settlement.accounting_entry.debit_amount, settlement.sale_revenue_entry.debit_amount), (60000, 30000))
        self.assertFalse(settlement.is_processed)  # 10,000 холбогдоогүй
        self.assertEqual(Sale.objects.get(pk=sales[0].pk).status, 'DRAFT')

        # Бүгдийг таслах — хоёр бичилт устаж, борлуулалт буцна
        self.client.post(link_page, {'unlink_type': 'all'})
        settlement.refresh_from_db()
        self.assertIsNone(settlement.accounting_entry)
        self.assertIsNone(settlement.sale_revenue_entry)
        self.assertFalse(AccountingEntry.objects.filter(debit_account=self.xac).exists())
        self.assertEqual(set(Sale.objects.values_list('status', flat=True)), {'DRAFT'})

    def test_link_more_than_settlement_rejected(self):
        from .models import Sale
        self.post_pos_sale(qty='1')
        self.post_pos_sale(qty='3')
        settlement, _ = self.add_statement(30000, 300)
        sales = list(Sale.objects.all())
        data = {'sale_ids': [str(s.id) for s in sales]}
        data.update({f'amount_{s.id}': str(s.total_amount) for s in sales})
        self.client.post(reverse('main:bank_transaction_link_sales', args=[settlement.id]), data)
        self.assertFalse(settlement.sale_allocations.exists())

    def test_sale_detail_suggests_settlement_of_sale_day(self):
        """Борлуулалт → гүйлгээ: өөр өдрийн, дүн таарсан сэттлмэнтээс илүү тухайн өдрийнхийг санал болгоно."""
        from datetime import timedelta
        from .models import BankTransaction, Sale
        self.post_pos_sale(qty='1')
        self.post_pos_sale(qty='3')
        sale = Sale.objects.get(total_amount=10000)
        other_day = BankTransaction.objects.create(
            account_type='BANK', bank_account=self.xac, transaction_date=self.sale_day - timedelta(days=2),
            description=f'{self.sale_day - timedelta(days=3):%Y.%m.%d}, 187, 44311091 СЕТТЛЕМЕНТ ХААВ', income_amount=10000)
        settlement, _ = self.add_statement(40000, 400)

        page = self.client.get(reverse('main:sale_detail', args=[sale.id]))
        txs = list(page.context['tx_page_obj'])
        self.assertEqual(txs[0].id, settlement.id)
        self.assertTrue(txs[0].is_pos_match)
        self.assertEqual(txs[0].default_link_amount, 10000)  # сэттлмэнтийн бүх дүн биш
        self.assertFalse(next(t for t in txs if t.id == other_day.id).is_exact)

        self.client.post(reverse('main:sale_link_bank', args=[sale.id]), {
            'transaction_id': str(settlement.id), 'action': 'link', 'link_amount': '10000'})
        sale.refresh_from_db(); settlement.refresh_from_db()
        self.assertEqual((sale.status, sale.paid_amount), ('PAID', 10000))
        self.assertEqual(settlement.accounting_entry.debit_amount, 10000)
        self.assertFalse(settlement.is_processed)  # 30,000 үлдсэн

    def test_pos_settlement_page_removed(self):
        from django.urls import NoReverseMatch
        with self.assertRaises(NoReverseMatch):
            reverse('main:pos_settlement_list')


class AutoLinkRuleTests(TestCase):
    """Автомат холболтын загвар: таарах, шалгаж хадгалах, импортлох үед шууд холбох."""

    def setUp(self):
        from decimal import Decimal
        from .models import AutoLinkRule, BankTransaction, CashFlowIndicator, ChartOfAccounts

        self.manager = make_profile('autolink', UserRole.DIRECTOR)
        self.client.force_login(self.manager.user)
        self.bank = ChartOfAccounts.objects.create(code='110101', name='ХААН БАНК', account_type='ASSET')
        self.fee_acc = ChartOfAccounts.objects.create(code='702701', name='Банкны шимтгэлийн зардал', account_type='EXPENSE')
        self.other_acc = ChartOfAccounts.objects.create(code='702301', name='Бусад зардал', account_type='EXPENSE')
        self.ind = CashFlowIndicator.objects.create(code='1.2.9', name='Бусад мөнгөн зарлага', flow_type='EXPENSE')
        AutoLinkRule.objects.all().delete()  # migration-ий анхдагч загварыг тестэд оруулахгүй
        self.rule = AutoLinkRule.objects.create(
            name='Банкны шимтгэл', keywords='шимтгэл, Charges for', direction='EXPENSE',
            offset_account=self.fee_acc, cash_flow_indicator=self.ind,
        )

        def tx(desc, income=0, expense=0):
            return BankTransaction.objects.create(
                account_type='BANK', bank_account=self.bank, transaction_date=date.today(),
                description=desc, income_amount=Decimal(income), expense_amount=Decimal(expense))
        self.fee1 = tx('Гүйлгээний  ШИМТГЭЛ', expense=200)
        self.fee2 = tx('Charges for PORD Customer Payment', expense=100)
        self.fee3 = tx('шимтгэл буцаалт', income=500)        # орлого — EXPENSE загварт таарахгүй
        self.other = tx('Түрээсийн төлбөр', expense=50000)   # үг таарахгүй

    def test_matching(self):
        from .auto_link import find_matches
        matched = {tx.id for tx, _ in find_matches()}
        self.assertEqual(matched, {self.fee1.id, self.fee2.id})

    def test_review_save_with_exclusion_and_edit(self):
        page = self.client.get(reverse('main:auto_link_review'))
        self.assertEqual(page.context['match_count'], 2)
        # fee1 — данс засаж хадгална, fee2 — хасна (include-д оруулахгүй)
        self.client.post(reverse('main:auto_link_review'), {
            'include': [str(self.fee1.id)],
            f'account_{self.fee1.id}': str(self.other_acc.id), f'indicator_{self.fee1.id}': str(self.ind.id),
            f'account_{self.fee2.id}': str(self.fee_acc.id),
        })
        self.fee1.refresh_from_db(); self.fee2.refresh_from_db()
        self.assertTrue(self.fee1.is_processed)
        self.assertEqual((self.fee1.offset_account, self.fee1.accounting_entry.debit_account,
                          self.fee1.accounting_entry.credit_account), (self.other_acc, self.other_acc, self.bank))
        self.assertFalse(self.fee2.is_processed)

    def test_auto_apply_on_import(self):
        from .auto_link import apply_auto_rules
        self.assertEqual(apply_auto_rules(self.manager.user), 0)   # auto_apply унтраалттай
        self.rule.auto_apply = True
        self.rule.save()
        self.assertEqual(apply_auto_rules(self.manager.user), 2)
        self.fee2.refresh_from_db(); self.other.refresh_from_db()
        self.assertEqual((self.fee2.is_processed, self.fee2.cash_flow_indicator), (True, self.ind))
        self.assertFalse(self.other.is_processed)

    def test_rule_crud(self):
        from .models import AutoLinkRule
        self.client.post(reverse('main:auto_link_rules'), {
            'name': 'Түрээс', 'keywords': 'түрээс', 'direction': 'EXPENSE',
            'offset_account': str(self.other_acc.id), 'priority': '50', 'is_active': 'on',
        })
        rule = AutoLinkRule.objects.get(name='Түрээс')
        self.assertEqual((rule.keyword_list, rule.priority, rule.auto_apply), (['түрээс'], 50, False))
        page = self.client.get(reverse('main:auto_link_rules'))
        counts = {r.name: r.match_count for r in page.context['rules']}
        self.assertEqual(counts['Түрээс'], 1)
        self.client.post(reverse('main:auto_link_rules'), {'action': 'delete', 'rule_id': str(rule.id)})
        self.assertFalse(AutoLinkRule.objects.filter(name='Түрээс').exists())


class SaleCogsTests(TestCase):
    """Борлуулалт бүртгэхэд өртгийн бичилт: Дт 610101 / Кт 150101 (өмнө нь "5101" кодоос болж үүсдэггүй байсан)."""

    def setUp(self):
        from .models import ChartOfAccounts, Product
        self.manager = make_profile('cogs', UserRole.DIRECTOR)
        self.client.force_login(self.manager.user)
        self.cash = ChartOfAccounts.objects.create(code='100100', name='Касс', account_type='ASSET')
        ChartOfAccounts.objects.create(code='510101', name='Борлуулалтын орлого', account_type='INCOME')
        self.inventory = ChartOfAccounts.objects.create(code='150101', name='Бараа материал', account_type='ASSET')
        self.cogs = ChartOfAccounts.objects.create(code='610101', name='Борлуулсан бүтээгдэхүүний өртөг', account_type='COST')
        self.product = Product.objects.create(code='P1', name='Ном', purchase_price=5000, selling_price=10000, initial_stock=10)

    def test_cash_sale_records_cogs(self):
        from .models import AccountingEntry, Sale
        self.client.post(reverse('main:sale_create_multi'), {
            'transaction_date': date.today().isoformat(), 'payment_method': 'CASH', 'cash_account': str(self.cash.id),
            'product_1': str(self.product.id), 'quantity_1': '3', 'price_1': '10000',
        })
        sale = Sale.objects.get()
        entry = AccountingEntry.objects.get(debit_account=self.cogs)
        self.assertEqual((entry.credit_account, entry.debit_amount, entry.related_sale), (self.inventory, 15000, sale))
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.credit_balance, 15000)
        page = self.client.get(reverse('main:sale_detail', args=[sale.id]))
        self.assertEqual(page.status_code, 200)
        self.assertGreaterEqual(page.context['journal_entries'].count(), 2)  # орлого + өртөг

    def test_opening_stock_syncs_inventory_account(self):
        self.client.post(reverse('main:product_opening_stock'), {
            f'qty_{self.product.id}': '20', f'cost_{self.product.id}': '4000',
        })
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.opening_balance, 80000)


class SaleEditTests(TestCase):
    """Борлуулалт засах — бүртгэх формтой ижил, дагалдах бичлэгүүд дахин үүснэ."""

    def setUp(self):
        from .models import ChartOfAccounts, Product
        self.manager = make_profile('editor', UserRole.DIRECTOR)
        self.client.force_login(self.manager.user)
        self.cash = ChartOfAccounts.objects.create(code='100100', name='Касс', account_type='ASSET')
        self.bank = ChartOfAccounts.objects.create(code='110101', name='ХААН БАНК', account_type='ASSET')
        self.xac = ChartOfAccounts.objects.create(code='110103', name='ХАС БАНК', account_type='ASSET')
        ChartOfAccounts.objects.create(code='510101', name='Борлуулалтын орлого', account_type='INCOME')
        self.inventory = ChartOfAccounts.objects.create(code='150101', name='Бараа материал', account_type='ASSET')
        ChartOfAccounts.objects.create(code='610101', name='Борлуулсан бүтээгдэхүүний өртөг', account_type='COST')
        self.p1 = Product.objects.create(code='P1', name='Ном', purchase_price=5000, selling_price=10000, initial_stock=10)
        self.p2 = Product.objects.create(code='P2', name='Лаа', purchase_price=1000, selling_price=3000, initial_stock=10)

    def create_cash_sale(self):
        from .models import Sale
        self.client.post(reverse('main:sale_create_multi'), {
            'transaction_date': date.today().isoformat(), 'payment_method': 'CASH',
            'cash_account': str(self.cash.id), 'create_cash_record': '1',
            'product_1': str(self.p1.id), 'quantity_1': '2', 'price_1': '10000',
        })
        return Sale.objects.get()

    def test_edit_page_prefills_same_form(self):
        sale = self.create_cash_sale()
        page = self.client.get(reverse('main:sale_finance_edit', args=[sale.id]))
        self.assertEqual(page.status_code, 200)
        self.assertTemplateUsed(page, 'main/sale_form_multi.html')
        data = page.context['edit_data']
        self.assertEqual((data['payment_method'], data['cash_account'], data['cash_record'], len(data['items'])),
                         ('CASH', self.cash.id, 'new', 1))
        self.assertContains(page, 'POS карт')  # бүртгэх формтой ижил төлбөрийн хэлбэрүүд

    def test_edit_rebuilds_movements_journal_and_cash(self):
        from .models import AccountingEntry, BankTransaction, Sale
        sale = self.create_cash_sale()
        number = sale.sale_number
        self.assertEqual(self.p1.current_stock, 8)
        # Бэлэн → Данс, Ном 2 → 1, Лаа 3 нэмэх
        self.client.post(reverse('main:sale_finance_edit', args=[sale.id]), {
            'transaction_date': date.today().isoformat(), 'payment_method': 'BANK', 'bank_account': str(self.bank.id),
            'product_1': str(self.p1.id), 'quantity_1': '1', 'price_1': '10000',
            'product_2': str(self.p2.id), 'quantity_2': '3', 'price_2': '3000',
        })
        sale = Sale.objects.get()
        self.assertEqual((sale.sale_number, sale.total_amount, sale.expected_payment_method), (number, 19000, 'Харилцах'))
        self.assertFalse(BankTransaction.objects.filter(account_type='CASH').exists())  # автомат касс устсан
        self.assertEqual((self.p1.current_stock, self.p2.current_stock), (9, 7))
        revenue = AccountingEntry.objects.get(related_sale=sale, credit_account__code='510101')
        self.assertEqual((revenue.debit_account, revenue.debit_amount), (self.bank, 19000))
        cogs = AccountingEntry.objects.get(related_sale=sale, debit_account__code='610101')
        self.assertEqual(cogs.debit_amount, 5000 + 3000)
        self.cash.refresh_from_db(); self.inventory.refresh_from_db()
        self.assertEqual(self.cash.debit_balance, 0)
        self.assertEqual(self.inventory.credit_balance, 8000)

    def test_pos_sale_date_edit(self):
        from datetime import timedelta
        from .models import Sale
        self.client.post(reverse('main:sale_create_multi'), {
            'transaction_date': date.today().isoformat(), 'payment_method': 'POS', 'pos_bank_account': str(self.xac.id),
            'product_1': str(self.p1.id), 'quantity_1': '1', 'price_1': '10000',
        })
        sale = Sale.objects.get()
        new_date = date.today() - timedelta(days=1)
        self.client.post(reverse('main:sale_finance_edit', args=[sale.id]), {
            'transaction_date': new_date.isoformat(), 'payment_method': 'POS', 'pos_bank_account': str(self.xac.id),
            'product_1': str(self.p1.id), 'quantity_1': '1', 'price_1': '10000',
        })
        sale.refresh_from_db()
        self.assertEqual((sale.sale_date, sale.pos_bank_account, sale.expected_payment_method), (new_date, self.xac, 'POS'))
        self.assertEqual(self.p1.current_stock, 9)

    def test_locked_sale_only_updates_notes(self):
        from decimal import Decimal
        from .models import BankTransaction, SalePaymentAllocation
        sale = self.create_cash_sale()
        tx = BankTransaction.objects.create(account_type='BANK', bank_account=self.bank, transaction_date=date.today(),
                                            description='Төлбөр', income_amount=Decimal('5000'))
        SalePaymentAllocation.objects.create(transaction=tx, sale=sale, amount=Decimal('5000'))
        page = self.client.get(reverse('main:sale_finance_edit', args=[sale.id]))
        self.assertTrue(page.context['locked_reasons'])
        self.client.post(reverse('main:sale_finance_edit', args=[sale.id]), {
            'notes': 'шинэ тэмдэглэл', 'payment_method': 'BANK', 'product_1': str(self.p1.id), 'quantity_1': '5', 'price_1': '1',
        })
        sale.refresh_from_db()
        self.assertEqual((sale.notes, sale.total_amount, sale.expected_payment_method), ('шинэ тэмдэглэл', 20000, 'Касс'))
        self.assertEqual(self.p1.current_stock, 8)

    def test_delete_restores_stock(self):
        from .models import AccountingEntry
        sale = self.create_cash_sale()
        self.client.post(reverse('main:sale_finance_delete', args=[sale.id]))
        self.assertEqual(self.p1.current_stock, 10)
        self.assertFalse(AccountingEntry.objects.exists())


class StudentPaymentsTests(TestCase):
    """Сурагчдын төлбөр: сар бүрийн төлөв (ирсэн ч төлөөгүй, дутуу, бүрэн) ба өр."""

    def setUp(self):
        from decimal import Decimal
        from .models import Attendance, BankTransaction, ChartOfAccounts, Enrollment, PaymentAllocation
        from .books_period import clear_start_date_cache
        from .models import FinanceSettings
        FinanceSettings.objects.filter(pk=1).update(books_start_date=None)  # migration-ы 2026-09-30
        clear_start_date_cache()
        self.addCleanup(clear_start_date_cache)
        self.admin = make_profile('spadmin', UserRole.DIRECTOR)
        self.admin.user.is_superuser = True
        self.admin.user.save()
        self.client.force_login(self.admin.user)
        course = make_course(name='Ахисан', level='ADVANCED')
        course.monthly_fee = Decimal('50000')
        course.save()
        bank = ChartOfAccounts.objects.create(code='110101', name='Банк', account_type='ASSET')
        tx = BankTransaction.objects.create(account_type='BANK', bank_account=bank, transaction_date=date(2026, 10, 2),
                                            description='төлбөр', income_amount=Decimal('80000'))

        def student(name, march_paid=None, attend_days=0):
            p = make_profile(name, UserRole.STUDENT, first_name=name)
            e = Enrollment.objects.create(student=p, course=course, status='APPROVED')
            for day in range(1, attend_days + 1):
                Attendance.objects.create(enrollment=e, date=date(2026, 3, day), present=True)
            if march_paid:
                PaymentAllocation.objects.create(transaction=tx, student=p, course=course, year=2026, month=3,
                                                 amount=Decimal(march_paid))
            return p
        self.unpaid = student('Төлөөгүй', attend_days=4)
        self.partial = student('Дутуу', march_paid=30000, attend_days=4)
        self.full = student('Бүрэн', march_paid=50000, attend_days=4)

    def test_states_and_debt(self):
        page = self.client.get(reverse('main:student_payments'), {'year': '2026', 'month': '3', 'course': 'all'})
        rows = {r['student'].first_name: r for c in page.context['table_data'] for r in c['enrollments']}
        self.assertEqual(rows['Төлөөгүй']['months_data'][3]['state'], 'unpaid')
        self.assertEqual(rows['Дутуу']['months_data'][3]['state'], 'partial')
        self.assertEqual(rows['Бүрэн']['months_data'][3]['state'], 'paid')
        self.assertEqual((rows['Төлөөгүй']['debt'], rows['Дутуу']['debt'], rows['Бүрэн']['debt']), (50000, 20000, 0))
        self.assertIn('unpaid', rows['Төлөөгүй']['flags'])
        self.assertIn('paid_ok', rows['Бүрэн']['flags'])
        # Төлсөн огноо нүдэнд жижгээр
        self.assertEqual(rows['Бүрэн']['months_data'][3]['paid_date_label'], '10/02')
        self.assertEqual(rows['Төлөөгүй']['months_data'][3]['paid_date_label'], '')
        self.assertContains(page, '📅 2026-10-02')

    def test_months_before_books_start_have_no_debt(self):
        from .books_period import clear_start_date_cache
        from .models import FinanceSettings
        settings_obj, _ = FinanceSettings.objects.get_or_create(pk=1)
        settings_obj.books_start_date = date(2026, 4, 1)
        settings_obj.save()
        clear_start_date_cache()
        self.addCleanup(clear_start_date_cache)

        unpaid, partial, full = (self._march_row(n) for n in ('Төлөөгүй', 'Дутуу', 'Бүрэн'))
        self.assertEqual((unpaid['months_data'][3]['state'], partial['months_data'][3]['state']), ('pre_start', 'pre_start'))
        self.assertEqual(full['months_data'][3]['state'], 'paid')
        self.assertEqual((unpaid['debt'], partial['debt']), (0, 0))
        self.assertNotIn('unpaid', unpaid['flags'])
        # Шүүлтүүд эхлэхээс өмнөх сарыг харахгүй
        self.assertNotIn('paid_ok', full['flags'])
        self.assertIn('never_paid', full['flags'])
        self.assertIn('never_attended', full['flags'])

        # Систем эхэлсэн сар (3-р сарын сүүлээр эхэлсэн ч) өрөнд тооцогдоно
        settings_obj.books_start_date = date(2026, 3, 30)
        settings_obj.save()
        clear_start_date_cache()
        row = self._march_row('Төлөөгүй')
        self.assertEqual((row['months_data'][3]['state'], row['debt']), ('unpaid', 50000))

    def test_discount_changes_state_and_debt(self):
        import json
        from .models import PaymentDiscount
        course = self.unpaid.enrollments.first().course
        url = reverse('main:payment_discount_save')

        def save(student, **extra):
            body = {'student': student.id, 'course': course.id, 'year': 2026, 'month': 3, **extra}
            return self.client.post(url, json.dumps(body), content_type='application/json').json()

        self.assertFalse(save(self.unpaid, name='Буруу', kind='PERCENT', value='150')['success'])
        self.assertFalse(save(self.unpaid, name='', kind='PERCENT', value='10')['success'])

        # Ирсэн ч эхний сар үнэгүй — төлөөгүй биш, өргүй
        self.assertTrue(save(self.unpaid, name='Эхний сар үнэгүй', kind='PERCENT', value='100', to_month='5')['success'])
        self.assertEqual(PaymentDiscount.objects.filter(student=self.unpaid).count(), 3)
        row = self._march_row('Төлөөгүй')
        cell = row['months_data'][3]
        self.assertEqual((cell['state'], cell['due'], row['debt']), ('discounted', 0, 0))
        self.assertEqual(cell['discount']['name'], 'Эхний сар үнэгүй')
        self.assertIn('discounted', row['flags'])

        # 20,000₮ хөнгөлөлт: 30,000 төлсөн нь бүрэн
        self.assertTrue(save(self.partial, name='Дахин элссэн', kind='AMOUNT', value='20000')['success'])
        row = self._march_row('Дутуу')
        self.assertEqual((row['months_data'][3]['state'], row['debt']), ('paid', 0))

        self.assertTrue(save(self.partial, delete=True)['success'])
        self.assertEqual(self._march_row('Дутуу')['months_data'][3]['state'], 'partial')

    def _march_row(self, name):
        page = self.client.get(reverse('main:student_payments'), {'year': '2026', 'month': '3', 'course': 'all'})
        rows = {r['student'].first_name: r for c in page.context['table_data'] for r in c['enrollments']}
        return rows[name]

    def test_pending_payment_marks_cell_and_matches_bank_allocation(self):
        import json
        from decimal import Decimal
        from .models import PaymentAllocation, PendingPayment
        course = self.unpaid.enrollments.first().course
        resp = self.client.post(reverse('main:pending_payment_create'), json.dumps({
            'student': self.unpaid.id, 'course': course.id, 'year': 2026, 'month': 3,
            'amount': '50000', 'paid_date': '2026-03-05', 'method': 'BANK', 'payer_name': 'Сараа',
        }), content_type='application/json')
        self.assertTrue(resp.json()['success'])
        pending = PendingPayment.objects.get()

        # Хуулга ирэхээс өмнө: өргүй, гэхдээ "Төлсөн" дүнд орохгүй
        row = self._march_row('Төлөөгүй')
        self.assertEqual(row['months_data'][3]['state'], 'pending')
        self.assertEqual(row['debt'], 0)
        self.assertEqual(row['visible_paid'], 0)
        self.assertIn('pending', row['flags'])

        # Хуулгын гүйлгээг холбоход автоматаар баталгаажна
        tx = PaymentAllocation.objects.first().transaction
        alloc = PaymentAllocation.objects.create(transaction=tx, student=self.unpaid, course=course,
                                                 year=2026, month=3, amount=Decimal('50000'))
        pending.refresh_from_db()
        self.assertEqual(pending.allocation, alloc)
        row = self._march_row('Төлөөгүй')
        self.assertEqual(row['months_data'][3]['state'], 'paid')
        self.assertEqual(row['months_data'][3]['transactions'][0]['pre_marked'], '2026-03-05')

        # Холбогдсон тэмдэглэлийг устгахгүй
        resp = self.client.post(reverse('main:pending_payment_delete', args=[pending.id]))
        self.assertFalse(resp.json()['success'])

        # Холболт цуцлагдвал дахин хүлээгдэнэ, тэгээд устгаж болно
        alloc.delete()
        pending.refresh_from_db()
        self.assertIsNone(pending.allocation)
        resp = self.client.post(reverse('main:pending_payment_delete', args=[pending.id]))
        self.assertTrue(resp.json()['success'])
        self.assertFalse(PendingPayment.objects.exists())

    def test_cash_payment_recorded_directly_to_cash_register(self):
        import json
        from .models import BankTransaction, CashFlowIndicator, ChartOfAccounts, PendingPayment
        ChartOfAccounts.objects.create(code='100100', name='Касс', account_type='ASSET')
        ChartOfAccounts.objects.create(code='510102', name='Сургалтын төлбөрийн орлого', account_type='INCOME')
        CashFlowIndicator.objects.create(code='1.1.1', name='Борлуулалт', flow_type='INCOME')
        course = self.unpaid.enrollments.first().course

        resp = self.client.post(reverse('main:pending_payment_create'), json.dumps({
            'student': self.unpaid.id, 'course': course.id, 'year': 2026, 'month': 3,
            'amount': '50000', 'paid_date': '2026-03-05', 'method': 'CASH', 'payer_name': 'Сараа',
        }), content_type='application/json')
        self.assertTrue(resp.json()['success'])

        self.assertFalse(PendingPayment.objects.exists())
        tx = BankTransaction.objects.get(account_type='CASH')
        self.assertEqual((tx.bank_account.code, tx.offset_account.code, tx.income_type), ('100100', '510102', 'STUDENT_PAYMENT'))
        self.assertTrue(tx.is_processed)
        self.assertIsNotNone(tx.accounting_entry)

        row = self._march_row('Төлөөгүй')
        self.assertEqual(row['months_data'][3]['state'], 'paid')
        self.assertEqual(row['visible_paid'], 50000)
        self.assertTrue(row['months_data'][3]['transactions'][0]['is_cash'])

    def test_pos_payment_marked_as_pending(self):
        import json
        from .models import PendingPayment
        course = self.unpaid.enrollments.first().course
        resp = self.client.post(reverse('main:pending_payment_create'), json.dumps({
            'student': self.unpaid.id, 'course': course.id, 'year': 2026, 'month': 3,
            'amount': '50000', 'paid_date': '2026-03-05', 'method': 'POS',
        }), content_type='application/json')
        self.assertTrue(resp.json()['success'])
        pending = PendingPayment.objects.get()
        self.assertEqual((pending.method, pending.amount), ('POS', 50000))
        self.assertEqual(self._march_row('Төлөөгүй')['months_data'][3]['state'], 'pending')

    def test_mixed_payment_splits_cash_and_bank(self):
        import json
        from .models import BankTransaction, CashFlowIndicator, ChartOfAccounts, PendingPayment
        ChartOfAccounts.objects.create(code='100100', name='Касс', account_type='ASSET')
        ChartOfAccounts.objects.create(code='510102', name='Сургалтын төлбөрийн орлого', account_type='INCOME')
        CashFlowIndicator.objects.create(code='1.1.1', name='Борлуулалт', flow_type='INCOME')
        course = self.unpaid.enrollments.first().course
        url = reverse('main:pending_payment_create')
        body = {'student': self.unpaid.id, 'course': course.id, 'year': 2026, 'month': 3,
                'amount': '50000', 'paid_date': '2026-03-05', 'method': 'MIXED'}

        # Бэлэн дүн нийт дүнгээс бага байх ёстой
        resp = self.client.post(url, json.dumps({**body, 'cash_amount': '50000'}), content_type='application/json')
        self.assertFalse(resp.json()['success'])

        resp = self.client.post(url, json.dumps({**body, 'cash_amount': '20000'}), content_type='application/json')
        self.assertTrue(resp.json()['success'])
        self.assertEqual(BankTransaction.objects.get(account_type='CASH').income_amount, 20000)
        pending = PendingPayment.objects.get()
        self.assertEqual((pending.method, pending.amount, pending.allocation), ('BANK', 30000, None))

        cell = self._march_row('Төлөөгүй')['months_data'][3]
        self.assertEqual((cell['payment'], cell['pending_amount'], cell['state']), (20000, 30000, 'pending'))

    def test_cash_before_books_start_marked_paid_without_journal(self):
        import json
        from .books_period import clear_start_date_cache
        from .models import BankTransaction, FinanceSettings, PaymentAllocation, PendingPayment
        settings_obj, _ = FinanceSettings.objects.get_or_create(pk=1)
        settings_obj.books_start_date = date(2026, 9, 1)
        settings_obj.save()
        clear_start_date_cache()
        self.addCleanup(clear_start_date_cache)
        self.admin.user.is_superuser = False
        self.admin.user.save()
        course = self.unpaid.enrollments.first().course
        url = reverse('main:pending_payment_create')
        body = {'student': self.unpaid.id, 'course': course.id, 'year': 2026, 'month': 3,
                'amount': '50000', 'paid_date': '2026-03-05'}

        resp = self.client.post(url, json.dumps({**body, 'method': 'MIXED', 'cash_amount': '20000'}),
                                content_type='application/json')
        self.assertTrue(resp.json()['success'])
        self.assertFalse(BankTransaction.objects.filter(account_type='CASH').exists())
        pre = PendingPayment.objects.get(pre_start=True)
        self.assertEqual((pre.method, pre.amount), ('CASH', 20000))

        self.admin.user.is_superuser = True
        self.admin.user.save()
        cell = self._march_row('Төлөөгүй')['months_data'][3]
        self.assertEqual((cell['payment'], cell['pending_amount']), (20000, 30000))
        self.assertEqual(cell['transactions'][0]['pre_start_id'], pre.id)

        # Банкны хуваарилалт журналгүй бичлэгийг биш, дансны тэмдэглэлийг холбоно
        tx = PaymentAllocation.objects.first().transaction
        PaymentAllocation.objects.create(transaction=tx, student=self.unpaid, course=course,
                                         year=2026, month=3, amount=30000)
        pre.refresh_from_db()
        self.assertIsNone(pre.allocation)
        self.assertIsNotNone(PendingPayment.objects.get(pre_start=False).allocation)

    def test_cell_note_save_update_and_clear(self):
        import json
        from .models import PaymentCellNote
        course = self.unpaid.enrollments.first().course
        url = reverse('main:payment_cell_note_save')

        def save(**extra):
            body = {'student': self.unpaid.id, 'course': course.id, 'year': 2026, 'month': 3, **extra}
            return self.client.post(url, json.dumps(body), content_type='application/json').json()

        self.assertTrue(save(comment='Ээж нь маргааш төлнө', color='#fecaca')['success'])
        self.assertTrue(save(comment='Шинэчилсэн', color='#bbf7d0')['success'])
        note = PaymentCellNote.objects.get()
        self.assertEqual((note.comment, note.color), ('Шинэчилсэн', '#bbf7d0'))

        row = self._march_row('Төлөөгүй')
        self.assertEqual(row['months_data'][3]['note'], {'comment': 'Шинэчилсэн', 'color': '#bbf7d0'})
        self.assertIn('noted', row['flags'])
        self.assertIn('Шинэчилсэн', row['notes_text'])

        self.assertFalse(save(comment='x', color='red; background:url(x)')['success'])
        self.assertTrue(save(comment='', color='')['success'])
        self.assertFalse(PaymentCellNote.objects.exists())

    def test_link_page_suggests_pending_payment(self):
        from decimal import Decimal
        from .bank_link_suggestions import suggest_pending_payments
        from .models import BankTransaction, ChartOfAccounts, PendingPayment
        course = self.unpaid.enrollments.first().course
        pending = PendingPayment.objects.create(student=self.unpaid, course=course, year=2026, month=10,
                                                amount=Decimal('50000'), paid_date=date(2026, 10, 1),
                                                payer_name='Сараа')
        PendingPayment.objects.create(student=self.partial, course=course, year=2026, month=10,
                                      amount=Decimal('90000'), paid_date=date(2026, 10, 1))
        old = PendingPayment.objects.create(student=self.full, course=course, year=2026, month=6,
                                            amount=Decimal('50000'), paid_date=date(2026, 6, 1))
        tx = BankTransaction.objects.create(account_type='BANK', bank_account=ChartOfAccounts.objects.get(code='110101'),
                                            transaction_date=date(2026, 10, 2), description='SARAA tolbor',
                                            income_amount=Decimal('50000'))
        result = suggest_pending_payments(tx, [])
        self.assertEqual([r['pending'] for r in result], [pending])  # 90000 > дүн, хуучин нь хасагдана
        self.assertTrue(result[0]['strong'])
        self.assertIn('Төлөгчийн нэр таарсан', result[0]['reasons'])
        self.assertNotIn(old, [r['pending'] for r in result])

        page = self.client.get(reverse('main:link_bank_transaction_to_journal', args=[tx.id]))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context['link_data']['pending_payments'][0]['id'], pending.id)


class BankLedgerTests(TestCase):
    """Банкны бүртгэл — кассын бүртгэл шиг: банк тус бүр эсвэл бүх банкны нийлсэн үлдэгдэл."""

    def setUp(self):
        from decimal import Decimal
        from .models import BankTransaction, ChartOfAccounts
        self.client.force_login(make_profile('ledger', UserRole.DIRECTOR).user)
        self.khan = ChartOfAccounts.objects.create(code='110101', name='ХААН БАНК', account_type='ASSET', opening_balance=Decimal('1000'))
        self.xac = ChartOfAccounts.objects.create(code='110103', name='ХАС БАНК', account_type='ASSET', opening_balance=Decimal('500'))
        today = date.today()
        BankTransaction.objects.create(account_type='BANK', bank_account=self.khan, transaction_date=today,
                                       description='орлого', income_amount=300, closing_balance=1300)
        BankTransaction.objects.create(account_type='BANK', bank_account=self.xac, transaction_date=today,
                                       description='зарлага', expense_amount=100, closing_balance=999)
        BankTransaction.objects.create(account_type='CASH', bank_account=self.khan, transaction_date=today,
                                       description='касс', income_amount=50)

    def test_all_banks_combined_and_single_bank(self):
        page = self.client.get(reverse('main:bank_transaction_ledger'))
        self.assertEqual((page.context['opening_balance'], page.context['closing_balance'], page.context['row_count']),
                         (1500, 1700, 2))  # кассын гүйлгээ орохгүй
        self.assertEqual([b['closing'] for b in page.context['account_balances']], [1300, 400])
        # ХАС-ийн хуулгын үлдэгдэл (999) тооцоолсонтой (400) зөрнө
        self.assertEqual([m['account'].code for m in page.context['balance_mismatches']], ['110103'])

        page = self.client.get(reverse('main:bank_transaction_ledger'), {'bank_account': self.khan.id})
        self.assertEqual((page.context['opening_balance'], page.context['closing_balance'], page.context['account_balances']),
                         (1000, 1300, []))

    def test_csv_export(self):
        response = self.client.get(reverse('main:bank_transaction_ledger'), {'export': 'csv'})
        self.assertIn('bank_tailan_', response['Content-Disposition'])


class ProductFormTests(TestCase):
    """Бараа нэмэх: борлуулах үнэ заавал биш, код автоматаар, алдаатай үед утга хадгалагдана."""

    def setUp(self):
        from .models import Product, ProductCategory
        self.client.force_login(make_profile('inv', UserRole.DIRECTOR).user)
        self.category = ProductCategory.objects.create(name='Лаа')
        Product.objects.create(code='400', name='Хадаг', purchase_price=1000, selling_price=2000)
        Product.objects.create(code='020156', name='Баркодтой', purchase_price=1, selling_price=2)

    def test_create_without_selling_price_and_auto_code(self):
        from .models import Product
        page = self.client.get(reverse('main:product_create'))
        self.assertEqual(page.context['form'].initial['code'], '401')  # 020156 тэгээр эхэлсэн тул тооцохгүй

        response = self.client.post(reverse('main:product_create'), {
            'name': '  Зул   лаа ', 'code': '', 'unit': 'PIECE', 'purchase_price': '12,500', 'selling_price': '',
        })
        product = Product.objects.get(name='Зул лаа')
        self.assertRedirects(response, reverse('main:inventory_list') + f'?highlight={product.id}', fetch_redirect_response=False)
        self.assertEqual((product.code, product.purchase_price, product.selling_price, product.initial_stock), ('401', 12500, 0, 0))

    def test_code_suggested_within_category_range(self):
        from .forms import product_code_suggestions, suggest_product_code
        from .models import Product, ProductCategory
        Product.objects.create(code='101', name='Лаа 1', purchase_price=1, selling_price=1, category=self.category)
        Product.objects.create(code='102', name='Лаа 2', purchase_price=1, selling_price=1, category=self.category)
        Product.objects.create(code='103', name='Ангилалгүй', purchase_price=1, selling_price=1)  # мужид ч давхцахгүй
        empty = ProductCategory.objects.create(name='Шинэ')
        self.assertEqual(suggest_product_code(self.category.id), '104')
        self.assertEqual(suggest_product_code(empty.id), '500')   # дараагийн чөлөөтэй зуут
        self.assertEqual(product_code_suggestions()[1], '401')

        # Код хоосон илгээвэл сонгосон ангиллын мужаас олгоно
        self.client.post(reverse('main:product_create'), {
            'name': 'Лаа 3', 'unit': 'PIECE', 'category': str(self.category.id), 'purchase_price': '0'})
        self.assertEqual(Product.objects.get(name='Лаа 3').code, '104')

    def test_duplicate_code_rejected_case_insensitively_and_values_kept(self):
        from .models import Product
        Product.objects.create(code='ABC-1', name='Хуучин', purchase_price=1, selling_price=1)
        response = self.client.post(reverse('main:product_create'), {
            'name': 'Шинэ бараа', 'code': 'abc-1', 'unit': 'PIECE', 'purchase_price': '500',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('code', response.context['form'].errors)
        self.assertContains(response, 'value="Шинэ бараа"')
        self.assertFalse(Product.objects.filter(name='Шинэ бараа').exists())

    def test_save_and_add_another_keeps_category_and_unit(self):
        response = self.client.post(reverse('main:product_create'), {
            'name': 'Бараа 1', 'unit': 'BOX', 'category': str(self.category.id), 'purchase_price': '0',
            'after_save': 'add_another',
        })
        self.assertRedirects(response, reverse('main:product_create') + f'?category={self.category.id}&unit=BOX',
                             fetch_redirect_response=False)
        page = self.client.get(response['Location'])
        self.assertContains(page, f'value="{self.category.id}" selected')
        self.assertContains(page, 'value="BOX" selected')

    def test_edit_keeps_initial_stock_and_clears_selling_price(self):
        from .models import Product
        product = Product.objects.create(code='P9', name='Ном', purchase_price=5000, selling_price=10000, initial_stock=7)
        self.client.post(reverse('main:product_edit', args=[product.id]), {
            'name': 'Ном', 'code': 'P9', 'unit': 'PIECE', 'purchase_price': '5000', 'selling_price': '',
            'initial_stock': '999', 'is_active': 'on',
        })
        product.refresh_from_db()
        self.assertEqual((product.initial_stock, product.selling_price, product.is_active), (7, 0, True))
