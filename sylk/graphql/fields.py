import graphene
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType


def camelCase(st):
    output = ''.join(x for x in st.title() if x.isalnum())
    return output[0].lower() + output[1:]


class EnhancedConnection(graphene.Connection):
    class Meta:
        abstract = True

    total_count = graphene.Int()

    def resolve_total_count(self, info):
        return self.count



class OrderedMongoengineConnectionField(MongoengineConnectionField):

    def __init__(self, type, *args, **kwargs):
        self.count = 0
        super(OrderedMongoengineConnectionField, self).__init__(
            type,
            *args,
            **dict(kwargs,orderBy=graphene.String())
        )

    def get_queryset(self, model, info, **args):
        order = args.pop('orderBy', None)
        qs = super(OrderedMongoengineConnectionField, self).get_queryset(model, info, **args)
        if order:
            order = camelCase(order)
            qs = qs.order_by(order)
        self.count = qs.count()
        return qs

    def default_resolver(self, _root, info, **args):
        connection = super(OrderedMongoengineConnectionField, self).default_resolver(_root, info, **args)
        connection.count = self.count
        return connection



