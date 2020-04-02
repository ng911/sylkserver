from graphene.relay import Node
from graphene.types import String, Field
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ...db.schema import Ticket as TicketModel
from ...db.schema import TicketNote as TicketNoteModel
from ...db.schema import Agent as AgentModel
from ...db.schema import User as UserModel
from ...db.schema import Email as EmailModel
from ...db.schema import Session as SessionModel
from .user import UserNode
from .session import SessionNode
from .agent import AgentNode
from .email import EmailNode

class TicketNoteNode(MongoengineObjectType):
    class Meta:
        model = TicketNoteModel
        interfaces = (Node,)


class TicketNode(MongoengineObjectType):
    class Meta:
        model = TicketModel
        interfaces = (Node,)

    active_chat = Field(SessionNode)
    active_sms = Field(SessionNode)
    sessions = MongoengineConnectionField(SessionNode)
    notes = MongoengineConnectionField(TicketNoteNode)
    emails = MongoengineConnectionField(EmailNode)
    user = Field(UserNode)
    primary_agent = Field(AgentNode)

    def resolve_active_chat(parent, info):
        try:
            return SessionModel.objects.get(ticketId=parent.ticketId, type='chat', status='active')
        except:
            return None

    def resolve_active_sms(parent, info):
        try:
            return SessionModel.objects.get(ticketId=parent.ticketId, type='sms', status='active')
        except:
            return None

    def resolve_sessions(parent, info, **args):
        params = {
            "ticketId" : parent.ticketId
        }
        if args != None:
            params.update(args)
        return SessionModel.objects(**params)

    def resolve_notes(parent, info, **args):
        params = {
            "ticketId" : parent.ticketId
        }
        if args != None:
            params.update(args)
        return TicketNoteModel.objects(**params)

    def resolve_emails(parent, info, **args):
        params = {
            "ticketId" : parent.ticketId
        }
        if args != None:
            params.update(args)
        return EmailModel.objects(**params)

    def resolve_user(parent, info):
        params = {
            "userId" : parent.userId
        }
        return UserModel.objects.get(**params)

    def resolve_primary_agent(parent, info):
        if (parent.primaryAgentId == None) or (parent.primaryAgentId == ""):
            return None
        params = {
            "userId" : parent.primaryAgentId
        }
        return AgentModel.objects.get(**params)



