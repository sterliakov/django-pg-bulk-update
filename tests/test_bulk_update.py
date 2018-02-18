from django.test import TestCase
from psycopg2.tests.testutils import skipIf

from django_pg_bulk_update import bulk_update
from django_pg_bulk_update.clause_operators import InClauseOperator
from django_pg_bulk_update.set_functions import ConcatSetFunction
from django_pg_bulk_update.utils import get_postgres_version
from tests.models import TestModel


class TestInputFormats(TestCase):
    fixtures = ['test_model']

    def test_model(self):
        with self.assertRaises(AssertionError):
            bulk_update(123, [])

        with self.assertRaises(AssertionError):
            bulk_update('123', [])

    def test_values(self):
        with self.assertRaises(AssertionError):
            bulk_update(TestModel, 123)

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [123])

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, {(1, 2): {'id': 10}})

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, {1: {'id': 10}}, key_fields=('id', 'name'))

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'name': 'test'}])

        self.assertEqual(1, bulk_update(TestModel, [{'id': 1, 'name': 'abc'}]))
        self.assertEqual(1, bulk_update(TestModel, [{'id': 1, 'name': 'abc', 'int_field': 2}],
                                        key_fields=('id', 'name')))
        self.assertEqual(1, bulk_update(TestModel, {1: {'name': 'abc'}}))
        self.assertEqual(1, bulk_update(TestModel, {(1,): {'name': 'abc'}}))
        self.assertEqual(1, bulk_update(TestModel, {(2, 'test2'): {'int_field': 2}}, key_fields=('id', 'name')))
        self.assertEqual(1, bulk_update(TestModel, {('test3',): {'int_field': 2}}, key_fields='name'))

    def test_key_fields(self):
        values = [{
            'id': 1,
            'name': 'bulk_update_1'
        }]

        self.assertEqual(1, bulk_update(TestModel, values))
        self.assertEqual(1, bulk_update(TestModel, values, key_fields='id'))
        self.assertEqual(1, bulk_update(TestModel, values, key_fields=['id']))
        self.assertEqual(1, bulk_update(TestModel, values, key_fields=['id', 'name']))
        self.assertEqual(1, bulk_update(TestModel, values, key_fields='name'))
        self.assertEqual(1, bulk_update(TestModel, values, key_fields=['name']))

    def test_using(self):
        values = [{
            'id': 1,
            'name': 'bulk_update_1'
        }]

        self.assertEqual(1, bulk_update(TestModel, values))
        self.assertEqual(1, bulk_update(TestModel, values, using='default'))

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, values, using='invalid')

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, values, using=123)

    def test_set_functions(self):
        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': 'test1'}], set_functions=123)

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': 'test1'}], set_functions=[123])

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': 'test1'}], set_functions={1: 'test'})

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': 'test1'}], set_functions={'id': 1})

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': 'test1'}], set_functions={'invalid': 1})

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': 'test1'}], set_functions={'int_field': 'invalid'})

        # int_field is not in update keys here, set_function
        with self.assertRaises(AssertionError):
            self.assertEqual(1, bulk_update(TestModel, [{'id': 2, 'name': 'test1'}], set_functions={'int_field': '+'}))

        # I don't test all set functions here, as there is another TestCase for this: TestSetFunctions
        self.assertEqual(1, bulk_update(TestModel, [{'id': 2, 'name': 'test1'}],
                                        set_functions={'name': ConcatSetFunction()}))
        self.assertEqual(1, bulk_update(TestModel, [{'id': 2, 'name': 'test1'}], set_functions={'name': '||'}))

    def test_key_fields_ops(self):
        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': 'test1'}], key_fields_ops=123)

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': 'test1'}], key_fields_ops=[123])

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': 'test1'}], key_fields_ops={123: 'test'})

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': 'test1'}], key_fields_ops={'id': 'invalid'})

        # name is not in key_fields
        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': ['test1']}], key_fields_ops={'name': 'in'})

        with self.assertRaises(AssertionError):
            bulk_update(TestModel, [{'id': 1, 'name': ['test1']}], key_fields_ops={'name': 123})

        self.assertEqual(1, bulk_update(TestModel, [{'id': [1], 'name': 'test1'}], key_fields_ops={'id': 'in'}))
        self.assertEqual(1, bulk_update(TestModel, [{'id': 1, 'name': ['test1']}], key_fields='name',
                                        key_fields_ops={'name': 'in'}))
        self.assertEqual(1, bulk_update(TestModel, [{'id': 1, 'name': ['test1']}], key_fields='name',
                                        key_fields_ops=['in']))
        self.assertEqual(1, bulk_update(TestModel, [{'id': [1], 'name': 'test1'}], key_fields_ops=['in']))
        self.assertEqual(1, bulk_update(TestModel, [{'id': [1], 'name': 'test1'}], key_fields_ops=[InClauseOperator()]))
        self.assertEqual(1, bulk_update(TestModel, [{'id': [1], 'name': 'test1'}],
                                        key_fields_ops={'id': InClauseOperator()}))


class TestSimple(TestCase):
    fixtures = ['test_model']

    def test_update(self):
        res = bulk_update(TestModel, [{
            'id': 1,
            'name': 'bulk_update_1'
        }, {
            'id': 5,
            'name': 'bulk_update_5'
        }, {
            'id': 8,
            'name': 'bulk_update_8'
        }])
        self.assertEqual(3, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {1, 5, 8}:
                self.assertEqual('bulk_update_%d' % pk, name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def test_empty(self):
        res = bulk_update(TestModel, [])
        self.assertEqual(0, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def test_quotes(self):
        res = bulk_update(TestModel, [{
            'id': 1,
            'name': '\''
        }, {
            'id': 5,
            'name': '"'
        }])
        self.assertEqual(2, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk == 1:
                self.assertEqual('\'', name)
            elif pk == 5:
                self.assertEqual('"', name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def test_key_update(self):
        res = bulk_update(TestModel, {
            ('test1',): {
                'id': 1,
                'name': 'bulk_update_1'
            },
            ('test5',): {
                'id': 5,
                'name': 'bulk_update_5'
            },
            ('test8',): {
                'id': 8,
                'name': 'bulk_update_8'
            }
        }, key_fields='name')
        self.assertEqual(3, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {1, 5, 8}:
                self.assertEqual('bulk_update_%d' % pk, name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def test_using(self):
        pass  # TODO


class TestSetFunctions(TestCase):
    fixtures = ['test_model']

    def test_incr(self):
        res = bulk_update(TestModel, [{
            'id': 1,
            'int_field': 1
        }, {
            'id': 5,
            'int_field': 5
        }, {
            'id': 8,
            'int_field': 8
        }], set_functions={'int_field': '+'})
        self.assertEqual(3, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {1, 5, 8}:
                self.assertEqual(2 * pk, int_field)
            else:
                self.assertEqual(pk, int_field)
            self.assertEqual('test%d' % pk, name)

    def test_concat_str(self):
        res = bulk_update(TestModel, [{
            'id': 1,
            'name': 'bulk_update_1'
        }, {
            'id': 5,
            'name': 'bulk_update_5'
        }, {
            'id': 8,
            'name': 'bulk_update_8'
        }], set_functions={'name': '||'})
        self.assertEqual(3, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {1, 5, 8}:
                self.assertEqual('test%dbulk_update_%d' % (pk, pk), name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def _test_concat_array(self, iteration, res):
        self.assertEqual(4, res)
        for pk, name, array_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'array_field'):
            if pk in {1, 2, 3}:
                self.assertListEqual([pk] * iteration, array_field)
            elif pk == 4:
                self.assertListEqual([], array_field)
            else:
                self.assertIsNone(array_field)
            self.assertEqual('test%d' % pk, name)

    def test_concat_array(self):
        for i in range(1, 5):
            res = bulk_update(TestModel, [{'id': 1, 'array_field': [1]},
                                          {'id': 2, 'array_field': [2]},
                                          {'id': 3, 'array_field': [3]},
                                          {'id': 4, 'array_field': []}], set_functions={'array_field': '||'})
            self._test_concat_array(i, res)

    def _test_concat_dict(self, iteration, res, field_name, val_as_str=False):
        self.assertEqual(4, res)
        for pk, name, dict_field in TestModel.objects.all().order_by('id').values_list('id', 'name', field_name):
            if pk in {1, 2, 3}:
                # Note that JSON standard uses only strings as keys. So json.dumps will convert it
                expected = {str(i): str(pk) if val_as_str else pk for i in range(1, iteration + 1)}
                self.assertDictEqual(expected, dict_field)
            elif pk == 4:
                self.assertDictEqual({}, dict_field)
            else:
                self.assertIsNone(dict_field)
            self.assertEqual('test%d' % pk, name)

    def test_concat_hstore(self):
        for i in range(1, 5):
            res = bulk_update(TestModel, [{'id': 1, 'hstore_field': {i: 1}},
                                          {'id': 2, 'hstore_field': {i: 2}},
                                          {'id': 3, 'hstore_field': {i: 3}},
                                          {'id': 4, 'hstore_field': {}}], set_functions={'hstore_field': '||'})
            self._test_concat_dict(i, res, 'hstore_field', val_as_str=True)

    @skipIf(get_postgres_version(as_tuple=False) < 90400, "JSONB type is available in PostgreSQL 9.4+ only")
    def test_concat_jsonb(self):
        for i in range(1, 5):
            res = bulk_update(TestModel, [{'id': 1, 'json_field': {i: 1}},
                                          {'id': 2, 'json_field': {i: 2}},
                                          {'id': 3, 'json_field': {i: 3}},
                                          {'id': 4, 'json_field': {}}], set_functions={'json_field': '||'})
            self._test_concat_dict(i, res, 'json_field')


class TestConditionOperators(TestCase):
    fixtures = ['test_model']

    def test_in(self):
        res = bulk_update(TestModel, [{
            'id': [1, 2, 3],
            'name': '1'
        }, {
            'id': [4, 5, 6],
            'name': '2'
        }], key_fields_ops=['in'])
        self.assertEqual(6, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {1, 2, 3}:
                self.assertEqual('1', name)
            elif pk in {4, 5, 6}:
                self.assertEqual('2', name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

        # Test not id field
        res = bulk_update(TestModel, [{
            'int_field': 1,
            'name': ['1']
        }, {
            'int_field': 2,
            'name': ['2']
        }], key_fields='name', key_fields_ops=['in'])
        self.assertEqual(6, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {1, 2, 3}:
                self.assertEqual(1, int_field)
            elif pk in {4, 5, 6}:
                self.assertEqual(2, int_field)
            else:
                self.assertEqual('test%d' % pk, name)

    def test_not_in(self):
        res = bulk_update(TestModel, [{
            'id': list(range(4, 10)),
            'name': '1'
        }, {
            'id': list(range(7, 10)) + list(range(1, 4)),
            'name': '2'
        }], key_fields_ops=['!in'])
        self.assertEqual(6, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {1, 2, 3}:
                self.assertEqual('1', name)
            elif pk in {4, 5, 6}:
                self.assertEqual('2', name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def test_not_equal(self):
        res = bulk_update(TestModel, [{
            'id': 1,
            'name': '1'
        }], key_fields_ops=['!eq'])
        self.assertEqual(8, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk != 1:
                self.assertEqual('1', name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def test_lt(self):
        res = bulk_update(TestModel, [{
            'id': 5,
            'name': '1'
        }], key_fields_ops=['<'])
        self.assertEqual(4, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {1, 2, 3, 4}:
                self.assertEqual('1', name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def test_lte(self):
        res = bulk_update(TestModel, [{
            'id': 5,
            'name': '1'
        }], key_fields_ops=['<='])
        self.assertEqual(5, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {1, 2, 3, 4, 5}:
                self.assertEqual('1', name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def test_gt(self):
        res = bulk_update(TestModel, [{
            'id': 5,
            'name': '1'
        }], key_fields_ops=['>'])
        self.assertEqual(4, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {6, 7, 8, 9}:
                self.assertEqual('1', name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def test_gte(self):
        res = bulk_update(TestModel, [{
            'id': 5,
            'name': '1'
        }], key_fields_ops=['>='])
        self.assertEqual(5, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {5, 6, 7, 8, 9}:
                self.assertEqual('1', name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)


class TestManager(TestCase):
    fixtures = ['test_model']

    def test_bulk_update(self):
        res = TestModel.objects.bulk_update([{
            'id': 1,
            'name': 'bulk_update_1'
        }, {
            'id': 5,
            'name': 'bulk_update_5'
        }, {
            'id': 8,
            'name': 'bulk_update_8'
        }])
        self.assertEqual(3, res)
        for pk, name, int_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'int_field'):
            if pk in {1, 5, 8}:
                self.assertEqual('bulk_update_%d' % pk, name)
            else:
                self.assertEqual('test%d' % pk, name)
            self.assertEqual(pk, int_field)

    def test_using(self):
        pass  # TODO


class TestFieldTypes(TestCase):
    fixtures = ['test_model']

    def test_array(self):
        res = bulk_update(TestModel, [{'id': 1, 'array_field': [1]},
                                      {'id': 2, 'array_field': [2]},
                                      {'id': 3, 'array_field': [3]},
                                      {'id': 4, 'array_field': []}])
        self.assertEqual(4, res)
        for pk, name, array_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'array_field'):
            if pk in {1, 2, 3}:
                self.assertListEqual([pk], array_field)
            elif pk == 4:
                self.assertListEqual([], array_field)
            else:
                self.assertIsNone(array_field)
            self.assertEqual('test%d' % pk, name)

    @skipIf(get_postgres_version(as_tuple=False) < 90400, "JSONB type is available in PostgreSQL 9.4+ only")
    def test_jsonb(self):
        res = bulk_update(TestModel, [{'id': 1, 'json_field': {'test': '1'}},
                                      {'id': 2, 'json_field': {'test': '2'}},
                                      {'id': 3, 'json_field': {'test': '3'}},
                                      {'id': 4, 'json_field': {}},
                                      {'id': 5, 'json_field': {'single': "'", "multi": '"'}}])
        self.assertEqual(5, res)
        for pk, name, json_field in TestModel.objects.all().order_by('id').values_list('id', 'name', 'json_field'):
            if pk in {1, 2, 3}:
                self.assertDictEqual({'test': str(pk)}, json_field)
            elif pk == 4:
                self.assertDictEqual({}, json_field)
            elif pk == 5:
                self.assertDictEqual({'single': "'", "multi": '"'}, json_field)
            else:
                self.assertIsNone(json_field)
            self.assertEqual('test%d' % pk, name)

    def test_hstore(self):
        res = bulk_update(TestModel, [{'id': 1, 'hstore_field': {'test': '1'}},
                                      {'id': 2, 'hstore_field': {'test': '2'}},
                                      {'id': 3, 'hstore_field': {'test': '3'}},
                                      {'id': 4, 'hstore_field': {}},
                                      {'id': 5, 'hstore_field': {'single': "'", "multi": '"'}}])
        self.assertEqual(5, res)
        for item in TestModel.objects.all().order_by('id'):
            if item.pk in {1, 2, 3}:
                self.assertDictEqual({'test': str(item.pk)}, item.hstore_field)
            elif item.pk == 4:
                self.assertDictEqual({}, item.hstore_field)
            elif item.pk == 5:
                self.assertDictEqual({'single': "'", "multi": '"'}, item.hstore_field)
            else:
                self.assertIsNone(item.hstore_field)
            self.assertEqual('test%d' % item.pk, item.name)