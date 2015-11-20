
class RTOEstimator:
    __rto           = 1000
    __estimated_rtt = 0
    __dev_rtt = 0

    @classmethod
    def get_rto_interval(cls):
        return cls.__rto

    # TODO: need a way to measure RTT
    @classmethod
    def update_rto_interval(cls, sample_rtt):
        cls.__estimated_rtt = cls.__estimated_rtt * 0.875 + 0.125 * sample_rtt
        cls.__dev_rtt = cls.__dev_rtt * 0.75 + 0.25 * abs(sample_rtt -
                                                          cls.__estimated_rtt)
        cls.__rto = cls.__estimated_rtt + 4 * cls.__dev_rtt

    @classmethod
    def rt_update(cls):
        cls.__rto *= 2
