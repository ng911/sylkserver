import graphene
from graphene.relay import Node

'''
from ..fields import OrderedMongoengineConnectionField
from .agent import AgentNode
from .ticket import TicketNode
from .session import SessionNode, SessionParticipantNode
from .company import PlanNode, CompanyNode, SubscriptionNode
from .user import UserNode
from .notification import NotificationNode
from .chat import MessageNode
from .email import EmailEventNode, EmailNode
from .company import CreateCompanyMutation, CompanyOnboardingMutation, UpdateCompanyMutation
from .user import UserProfileMutation
from .notification import NotificationReadMutation
from .landingpage import LandingPageNode

class Query(graphene.ObjectType):
    node = Node.Field()
    all_agents = OrderedMongoengineConnectionField(AgentNode)
    all_tickets = OrderedMongoengineConnectionField(TicketNode)
    all_sessions = OrderedMongoengineConnectionField(SessionNode)
    all_plans = OrderedMongoengineConnectionField(PlanNode)
    all_companies = OrderedMongoengineConnectionField(CompanyNode)
    company = graphene.Field(CompanyNode)
    agent = graphene.Field(AgentNode)
    user = graphene.Field(UserNode)
    subscription = graphene.Field(SubscriptionNode)
    all_notifications = OrderedMongoengineConnectionField(NotificationNode)
    all_messages = OrderedMongoengineConnectionField(MessageNode)
    all_emails = OrderedMongoengineConnectionField(EmailNode)
    all_email_events = OrderedMongoengineConnectionField(EmailEventNode)
    landing_page_data = OrderedMongoengineConnectionField(LandingPageNode)

class Mutations(
    CreateCompanyMutation,
    NotificationReadMutation,
    CompanyOnboardingMutation,
    UpdateCompanyMutation,
    UserProfileMutation,
    graphene.ObjectType,
):
    pass

graphql_schema = graphene.Schema(query=Query, types=[AgentNode, PlanNode, CompanyNode, SubscriptionNode, \
                                             TicketNode, NotificationNode, SessionParticipantNode, \
                                             EmailNode, EmailEventNode], \
                         mutation=Mutations)
'''
class Query(graphene.ObjectType):
    node = Node.Field()

    name = graphene.String()

    def resolve_name(parent, info, **args):
        return "Hello World"


graphql_schema = graphene.Schema(query=Query, types=[])

__all__ = [ 'graphql_schema']
