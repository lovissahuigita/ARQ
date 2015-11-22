from RxP.Packeter import Packeter

class CongestionControl:

    __congestion_window = 1  # segment
    __state = True  # True = slow start, False = congestion avoidance
    __threshold = 0


    @classmethod
    def got_new_ack(cls):
        if cls.__state:
            cls.__congestion_window += Packeter.MSS
        else:
            cls.__congestion_window += (Packeter.MSS * Packeter.MSS)/cls.__congestion_window
        cls.__update_state()

    @classmethod
    def report_missing_packet(cls):
        cls.__threshold = cls.__congestion_window/2
        cls.__congestion_window = 1
        cls.__update_state()
        # cls.__state = True TODO: which one makes more sense?




    @classmethod
    def __update_state(cls):
        cls.__state = (cls.__congestion_window <= cls.__threshold)

        # TODO: dont forget to send 1byte data if peer receive windows is full