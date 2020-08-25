import logging
import graphene
from mongoengine import *

log = logging.getLogger("emergent-ng911")


def _get_graphene_fied_for_mongoengine(field):
    if isinstance(field, ObjectIdField) or isinstance(field, StringField):
        return graphene.String()
    if isinstance(field, BooleanField):
        return graphene.Boolean()
    if isinstance(field, IntField):
        return graphene.Int()


def _create_input_class(model_class):
    input_class = type('Input', (object, ), {})
    fields = []
    for field, val in model_class._fields.items():
        #print(f"field {field} type {val.__class__.__name__} required {val.required}")
        graphene_field = _get_graphene_fied_for_mongoengine(val)
        if graphene_field != None:
            setattr(input_class, field, graphene_field)
            fields.append(field)
    return input_class, fields

def _create_input_class_delete():
    return type('Input', (object, ), {"id" : graphene.ID(required=True)})


def _mutate_and_get_payload_for_update(model_class, fields, key):
    def mutate_and_get_payload(cls, root, info, **input):
        params = {
            key: input.get(key)
        }
        db_obj = model_class.objects.get(**params)
        for field in fields:
            if field != key:
                val = input.get(field)
                if val != None:
                    setattr(db_obj, field, val)
        db_obj.save()
        prop_name = model_class._get_collection_name()
        params = {
            prop_name : db_obj
        }
        return cls(**params)
    return mutate_and_get_payload


def _mutate_and_get_payload_for_insert(model_class, fields):
    def mutate_and_get_payload(cls, root, info, **input):
        db_obj = model_class()
        for field in fields:
            val = input.get(field)
            if val != None:
                setattr(db_obj, field, val)
        db_obj.save()
        prop_name = model_class._get_collection_name()
        params = {
            prop_name : db_obj
        }
        return cls(**params)
    return mutate_and_get_payload

def _mutate_and_get_payload_for_delete(model_class):
    def mutate_and_get_payload(cls, root, info, **input):
        id_ = input.get("id")
        try:
            db_obj = model_class.objects.get(pk=id_).delete()
            success = True
        except DoesNotExist:
            success = False
        return cls(success = success)
    return mutate_and_get_payload

def create_insert_mutation(cls, model_class, node_class):
    input_class, fields = _create_input_class(model_class)
    prop_name = model_class._get_collection_name()
    setattr(cls, "Input", input_class)
    setattr(cls, prop_name, graphene.Field(node_class))
    _create_mutate_method = _mutate_and_get_payload_for_insert(model_class, fields)
    setattr(cls, "mutate_and_get_payload", classmethod(_create_mutate_method))
    return cls

def create_update_mutation(cls, model_class, node_class, key):
    input_class, fields = _create_input_class(model_class)
    prop_name = model_class._get_collection_name()
    setattr(cls, "Input", input_class)
    setattr(cls, prop_name, graphene.Field(node_class))
    _create_mutate_method = _mutate_and_get_payload_for_update(model_class, fields, key)
    setattr(cls, "mutate_and_get_payload", classmethod(_create_mutate_method))
    return cls

def create_delete_mutation(cls, model_class):
    input_class = _create_input_class_delete()
    setattr(cls, "Input", input_class)
    setattr(cls, "success", graphene.Boolean())
    _create_mutate_method = _mutate_and_get_payload_for_delete(model_class)
    setattr(cls, "mutate_and_get_payload", classmethod(_create_mutate_method))
    return cls

'''
class DeleteBikeMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(self, info, id):
        try:
            Bike.objects.get(pk=id).delete()
            success = True
        except ObjectDoesNotExist:
            success = False

        return DeleteBikeMutation(success=success)
        
'''


class EnhancedClientIDMutation(graphene.relay.ClientIDMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls, output=None, input_fields=None, arguments=None, name=None, **options
    ):
        cls.__custom__()
        super(EnhancedClientIDMutation, cls).__init_subclass_with_meta__(
            output=output, arguments=arguments, name=name, **options
        )

    @classmethod
    def __custom__(cls):
        pass

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        pass

