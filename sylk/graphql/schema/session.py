from graphene.relay import Node
from graphene.types import String, Field
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType

from ...db.schema import Company as CompanyModel
from ...db.schema import BotUser as BotUserModel
from ...db.schema import SessionParticipant as SessionParticipantModel
from ...db.schema import UserProfile as UserProfileModel
from ...db.schema import Agent as AgentModel
from ...db.schema import User as UserModel
from ...db.schema import Session as SessionModel
from ...db.schema import ChatMessage as MessageModel
from .user import UserNode
from .chat import MessageNode



class SessionParticipantNode(MongoengineObjectType):
    class Meta:
        model = SessionParticipantModel
        interfaces = (Node,)
    photo_url = String()
    name = String()

    def get_participant_details(parent):
        name = None
        photo_url = None

        if parent.participantType == "bot":
            botUserObj = BotUserModel.objects.get(botId=parent.participant)
            if hasattr(botUserObj, "profileId") and (botUserObj.profileId != None) and (botUserObj.profileId != ""):
                userProfileObj = UserProfileModel.objects.get(profileId=botUserObj.profileId)
                name = userProfileObj.displayName
                photo_url = userProfileObj.photoUrl
            else:
                companyId = botUserObj.companyId
                companyObj = CompanyModel.objects.get(companyId=companyId)
                name = companyObj.profileName
                photo_url = companyObj.profilePhoto

        if parent.participantType == "agent":
            agentObj = AgentModel.objects.get(userId=parent.participant)
            name = agentObj.name
            photo_url = agentObj.photoUrl

        if parent.participantType == "customer":
            userObj = UserModel.objects.get(userId=parent.participant)
            name = userObj.name
            photo_url = userObj.photoUrl

        parent.name = name
        parent.photo_url = photo_url

    def resolve_photo_url(parent, info):
        if not hasattr(parent, "name") or (parent.name == None):
            SessionParticipantNode.get_participant_details(parent)
        return parent.photo_url

    def resolve_name(parent, info):
        #(name, photo_url) = SessionParticipantNode.get_participant_details(parent)
        if not hasattr(parent, "name") or (parent.name == None):
            SessionParticipantNode.get_participant_details(parent)
        return parent.name


class SessionNode(MongoengineObjectType):
    class Meta:
        model = SessionModel
        interfaces = (Node,)
    session_participants = MongoengineConnectionField(SessionParticipantNode)
    chat_messages = MongoengineConnectionField(MessageNode)
    customer = Field(UserNode)

    def resolve_customer(parent, info):
        try:
            participantObj = SessionParticipantModel.objects.get(sessionId=parent.sessionId, participantType="customer")
            userId = participantObj.participant
            return UserModel.objects.get(userId=userId)
        except:
            return None


    def resolve_session_participants(parent, info, **args):
        params = {
            "sessionId" : parent.sessionId
        }
        if args != None:
            params.update(args)
        return SessionParticipantModel.objects(**params)

    def resolve_chat_messages(parent, info, **args):
        params = {
            "sessionId" : parent.sessionId
        }
        return MessageModel.objects(**params)


