import logging
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType
from graphene import String
import graphene
from ..db.schema import Company
from graphene_mongo.registry import get_global_registry

logger = logging.getLogger('kingfisher')


def resolve_full_name(parent, info):
    return "Hello World there"

def convert_lazy_foreign_key_field(field_name, model, foreign_attr, registry=None):
    def lazy_resolver(root, *args, **kwargs):
        if getattr(root, field_name):
            filter = {
                foreign_attr : getattr(root, field_name)
            }
            #logger.debug("companyId is %r", companyId)
            return model.objects.get(**filter)

    def dynamic_type():
        _type = registry.get_type_for_model(model)
        if not _type:
            assert(False)
            return None
        return graphene.Field(
            _type,
            resolver=lazy_resolver,
            description="foreign key field",
        )

    return graphene.Dynamic(dynamic_type)

# from for class Meta https://github.com/graphql-python/graphene-mongo/issues/68
class EnhancedMongoengineObjectType(MongoengineObjectType):

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        foreign_keys=None,
        model=None,
        registry=None,
        skip_registry=False,
        only_fields=(),
        exclude_fields=(),
        filter_fields=None,
        connection=None,
        connection_class=None,
        use_connection=None,
        connection_field_class=None,
        interfaces=(),
        _meta=None,
        **options
    ):
        if not registry:
            registry = get_global_registry()

        #setattr(cls, "full_name", String())
        #cls.resolve_full_name = resolve_full_name
        if foreign_keys is not None:
            for foreign_key in foreign_keys:
                field_name = foreign_key["name"]
                lk = foreign_key["lk"]
                fk = foreign_key["fk"]
                fk_model = foreign_key["fk_model"]
                field_value = convert_lazy_foreign_key_field(lk, fk_model, fk, registry)
                setattr(cls, field_name, field_value)
        #field_value = convert_lazy_foreign_key_field("companyId", Company, "companyId", registry)
        #setattr(cls, "company", field_value)
        super(EnhancedMongoengineObjectType, cls).__init_subclass_with_meta__(
            model,
            registry,
            skip_registry,
            only_fields,
            exclude_fields,
            filter_fields,
            connection,
            connection_class,
            use_connection,
            connection_field_class,
            interfaces,
            _meta,
            **options
        )


