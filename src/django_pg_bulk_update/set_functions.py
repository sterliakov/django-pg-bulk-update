"""
This file contains classes, describing functions which set values to fields.
"""
from django.db import DefaultConnectionProxy
from django.db.models import Field
from typing import Type, Optional, Any, Tuple

from .utils import get_subclasses, format_field_value

# When doing increment operations, we need to replace NULL values with something
# This dictionary contains field defaults by it's class name.
# I don't use classes as keys not to import them here
NULL_DEFAULTS = {
    # Standard django types
    'IntegerField': 0,
    'FloatField': 0,
    'CharField': '',
    'TextField': '',


    # Postgres specific types
    'ArrayField': [],
    'CICharField': '',
    'CIEmailField': '',
    'CITextField': '',
    'HStoreField': {},
    'JSONField': {}

    # TODO django.contrib.postgres.fields.ranges
    # 'RangeField':
}


class AbstractSetFunction(object):
    names = set()

    # If set function supports any field class, this should be None.
    # Otherwise a set of class names supported
    supported_field_classes = None

    def format_field_value(self, field, val, connection, **kwargs):
        # type: (Field, Any, DefaultConnectionProxy, **Any) -> Tuple[str, Tuple[Any]]
        """
        Formats value, according to field rules
        :param field: Django field to take format from
        :param val: Value to format
        :param connection: Connection used to update data
        :param kwargs: Additional arguments, if needed
        :return: A tuple: sql, replacing value in update and a tuple of parameters to pass to cursor
        """
        return format_field_value(field, val, connection)

    def get_sql(self, field, val, connection, val_as_param=True, **kwargs):
        # type: (Field, Any, DefaultConnectionProxy, bool, **Any) -> Tuple[str, Tuple[Any]]
        """
        Returns function sql and parameters for query execution
        :param model: Model updated
        :param field: Django field to take format from
        :param val: Value to format
        :param connection: Connection used to update data
        :param val_as_param: If flag is not set, value should be converted to string and inserted into query directly.
            Otherwise a placehloder and query parameter will be used
        :param kwargs: Additional arguments, if needed
        :return: A tuple: sql, replacing value in update and a tuple of parameters to pass to cursor
        """
        raise NotImplementedError("'%s' must define get_sql method" % self.__class__.__name__)

    @classmethod
    def get_function_by_name(cls, name):  # type: (str) -> Optional[Type[AbstractSetFunction]]
        """
        Finds subclass of AbstractOperation applicable to given operation name
        :param name: String name to search
        :return: AbstractOperation subclass if found, None instead
        """
        try:
            return next(sub_cls for sub_cls in get_subclasses(cls, recursive=True) if name in sub_cls.names)
        except StopIteration:
            raise AssertionError("Operation with name '%s' doesn't exist" % name)

    def field_is_supported(self, field):  # type: (Field) -> bool
        """
        Tests if this set function supports given field
        :param field: django.db.models.Field instance
        :return: Boolean
        """
        if self.supported_field_classes is None:
            return True
        else:
            return field.__class__.__name__ in self.supported_field_classes

    def _parse_null_default(self, field, connection, **kwargs):
        """
        Part of get_function_sql() method.
        When operation is done on the bases of field's previous value, we need a default to set instead of NULL.
        This function gets this default value.
        :param field: Field to set default for
        :param connection: Connection used to update data
        :param kwargs: kwargs of get_function_sql
        :return: null_default value
        """
        if 'null_default' in kwargs:
            null_default = kwargs['null_default']
        elif field.__class__.__name__ in NULL_DEFAULTS:
            null_default = NULL_DEFAULTS[field.__class__.__name__]
        else:
            raise Exception("Operation '%s' doesn't support field '%s'"
                            % (self.__class__.__name__, field.__class__.__name__))

        return self.format_field_value(field, null_default, connection)


class EqualSetFunction(AbstractSetFunction):
    names = {'eq', '='}

    def get_sql(self, field, val, connection, val_as_param=True, **kwargs):
        if val_as_param:
            sql, params = self.format_field_value(field, val, connection)
            return '"%s" = %s' % (field.column, sql), params
        else:
            return '"%s" = %s' % (field.column, str(val)), []


class PlusSetFunction(AbstractSetFunction):
    names = {'+', 'incr'}

    # TODO list all supported classes from django.db.models.fileds
    supported_field_classes = {'IntegerField', 'FloatField', 'AutoField', 'BigAutoField'}

    def get_sql(self, field, val, connection, val_as_param=True, **kwargs):
        null_default, null_default_params = self._parse_null_default(field, connection, **kwargs)
        tpl = '"%s" = COALESCE("%s", %s) + %s'

        if val_as_param:
            sql, params = self.format_field_value(field, val, connection)
            return tpl % (field.column, field.column, null_default, sql), null_default_params + params
        else:
            return tpl % (field.column, field.column, null_default, str(val)), null_default_params


class ConcatSetFunction(AbstractSetFunction):
    names = {'||', 'concat'}

    # TODO list all supported classes from django.db.models.fileds
    supported_field_classes = {'CharField', 'TextField', 'HStoreField', 'JSONField', 'ArrayField', 'CITextField',
                               'CICharField', 'CIEmailField'}

    def get_sql(self, field, val, connection, val_as_param=True, **kwargs):
        null_default, null_default_params = self._parse_null_default(field, connection, **kwargs)
        tpl = '"%s" = COALESCE("%s", %s) || %s'

        if val_as_param:
            sql, params = self.format_field_value(field, val, connection)
            return tpl % (field.column, field.column, null_default, sql), null_default_params + params
        else:
            return tpl % (field.column, field.column, null_default, str(val)), null_default_params