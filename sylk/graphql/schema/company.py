import graphene
from graphene.relay import Node
from graphene_mongo import MongoengineObjectType

from ...db.schema import Plan as PlanModel
from ...db.schema import Subscription as SubscriptionModel
from ...db.schema import Company as CompanyModel
from ..fields import EnhancedConnection
from ...db.schema import Agent as AgentModel
from .agent import AgentNode


class PlanNode(MongoengineObjectType):
    class Meta:
        model = PlanModel
        interfaces = (Node,)
        connection_class = EnhancedConnection


class CompanyNode(MongoengineObjectType):
    class Meta:
        model = CompanyModel
        interfaces = (Node,)


class SubscriptionNode(MongoengineObjectType):
    class Meta:
        model = SubscriptionModel
        interfaces = (Node,)


class RelayUpdateCompanyMutation(graphene.relay.ClientIDMutation):
    company = graphene.Field(CompanyNode)

    class Input:
        companyId = graphene.String()
        website = graphene.String()
        name = graphene.String()
        email = graphene.String()
        photoUrl = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        #user = info.context.user or None
        companyId = input.get('companyId')
        website = input.get('website')
        name = input.get('name')
        email = input.get('email')
        photoUrl = input.get('photoUrl')
        CompanyObj = CompanyModel.objects.get(companyId=companyId)
        CompanyObj.website = website
        CompanyObj.name = name
        CompanyObj.email = email
        CompanyObj.photoUrl = photoUrl
        CompanyObj.save()

        return RelayUpdateCompanyMutation(company=CompanyObj)


class UpdateCompanyMutation(graphene.AbstractType):
    relay_update_company = RelayUpdateCompanyMutation.Field()


class RelayCompanyOnboardingMutation(graphene.relay.ClientIDMutation):
    company = graphene.Field(CompanyNode)

    class Input:
        onboarding = graphene.String()
        companyId = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        companyId = input.get('companyId')
        onboarding = input.get('onboarding')
        CompanyObj = CompanyModel.objects.get(companyId=companyId)
        CompanyObj.onboarding = onboarding
        CompanyObj.save()

        return RelayCompanyOnboardingMutation(company=CompanyObj)

class RelayCreateCompanyMutation(graphene.relay.ClientIDMutation):
    company = graphene.Field(CompanyNode)
    agent = graphene.Field(AgentNode)

    class Input:
        companyName = graphene.String()
        agentEmail = graphene.String()
        agentName = graphene.String()
        agentPassword = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        #user = info.context.user or None

        company = CompanyModel(
            name=input.get('companyName'),
        )
        company.save()
        agent = AgentModel()
        agent.companyId = company.companyId
        agent.name = input.get('agentName')
        agent.email = agent.loginId = input.get('agentEmail')
        agent.passwordHash = AgentModel.generate_password_hash(input.get('agentPassword'))
        agent.save()

        return RelayCreateCompanyMutation(company=company, agent=agent)

class CreateCompanyMutation(graphene.AbstractType):
    relay_create_company = RelayCreateCompanyMutation.Field()


class CompanyOnboardingMutation(graphene.AbstractType):
    relay_company_onboarding = RelayCompanyOnboardingMutation.Field()


