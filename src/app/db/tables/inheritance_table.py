from datetime import UTC, datetime

from tortoise import fields, manager, models, queryset


class CustomQuerySet(queryset.QuerySet):
    async def update(self, **kwargs):
        """
        A custom QuerySet that overrides the update method to automatically
        update the 'modified_at' field with the current timestamp.

        This QuerySet ensures that any bulk update operation will update
        the 'modified_at' field for all affected records.

        Example:
            await MyModel.filter(some_field=some_value).update(other_field=new_value)
            # This will also update 'modified_at' for all matched records
        """
        kwargs["modified_at"] = datetime.now(UTC)
        return await super().update(**kwargs)


class CustomManager(manager.Manager):
    def get_queryset(self) -> CustomQuerySet:
        """
        Override the default get_queryset method to return our CustomQuerySet.

        Example:
            # This will use CustomQuerySet for all operations
            MyModel.all()
            MyModel.filter(some_field=some_value)
        """
        return CustomQuerySet(self._model)


class TimestampMixin(models.Model):
    """
    A mixin class that adds timestamp fields and a status field to a model.

    Attributes:
        created_at (DatetimeField): The date and time when the record was created.
            Automatically set to the current date and time when the record is first created.
        modified_at (DatetimeField): The date and time when the record was last modified.
            Automatically updated to the current date and time whenever the record is saved.
        status (BooleanField): A boolean field indicating the status of the record.
            Defaults to True.

    Meta:
        abstract (bool): Indicates that this is an abstract base class.
    """

    # dates
    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    modified_at = fields.DatetimeField(null=True, auto_now=True)
    # row status
    status = fields.BooleanField(default=True)

    class Meta:
        abstract = True
