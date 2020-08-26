from application import log

class VideoConferenceSession(object):
    def __init__(self, video_mixer, video_stream):
        log.info("inside VideoConferenceSession __init__ %r", video_stream)
        self.video_mixer = video_mixer
        self.consumer_port = video_stream._transport.remote_video_stream.consumer_port
        log.info("inside VideoConferenceSession self.consumer_port %r", self.consumer_port)
        self.producer_port = video_stream._transport.local_video_stream.producer_port
        log.info("inside VideoConferenceSession self.consumer_port %r", self.producer_port)
        self.source_slot = video_mixer._add_port(self.producer_port)
        log.info("inside VideoConferenceSession self.source_slot %r", self.source_slot)
        self.sink_slot = video_mixer._add_port(self.consumer_port)
        log.info("inside VideoConferenceSession self.sink_slot %r", self.sink_slot)

    def connect_sink(self, sink_slot):
        log.info("inside VideoConferenceSession connect_sink self.source_slot %r, connect_sink %r", self.source_slot, sink_slot)
        self.video_stream.connect_slots(self.source_slot, sink_slot)
        log.info("inside VideoConferenceSession connect_sink done")


class VideoConference(object):
    def __init__(self, video_mixer):
        log.info("inside VideoConference __init__")
        self.video_mixer = video_mixer
        self.rooms = {}

    def add_to_room(self, room_number, video_stream):
        log.info("inside VideoConference add_to_room room_number %r, video_stream %r", room_number, video_stream)
        if room_number in self.rooms:
            log.info("inside VideoConference found room_data")
            room_data = self.rooms[room_number]
        else:
            log.info("inside VideoConference add room_data")
            room_data = { "sessions" : ""}
            self.rooms[room_number] = room_data
        sessions = room_data["sessions"]
        log.info("inside VideoConference sessions %r", sessions)
        session = VideoConferenceSession(self.video_mixer, video_stream)
        for room_session in sessions:
            log.info("add room_session %r", room_session)
            room_session.connect_sink(session.sink_slot)
            log.info("room_session connect_sink done")
            session.connect_sink(room_session.sink_slot)
            log.info("session connect_sink done")
        sessions.append(session)
        log.info("add_to_room done")
