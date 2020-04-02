import graphene
from graphene.relay import Node
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ..fields import OrderedMongoengineConnectionField, EnhancedConnection
from ...db.schema import Notification as NotificationModel


class NotificationNode(MongoengineObjectType):
    class Meta:
        model = NotificationModel
        interfaces = (Node,)
        connection_class = EnhancedConnection


class RelayNotificationReadMutation(graphene.relay.ClientIDMutation):
    notification = graphene.Field(NotificationNode)

    class Input:
        notifciationId = graphene.String()
        userId = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        #user = info.context.user or None
        notifciationId = input.get('notifciationId')
        userId = input.get('userId')
        notificationObj = NotificationModel.objects.get(notifciationId=notifciationId, userId=userId)
        notificationObj.unread = False
        notificationObj.save()

        return RelayNotificationReadMutation(notification=notificationObj)

class NotificationReadMutation(graphene.AbstractType):
    relay_notification_read = RelayNotificationReadMutation.Field()


