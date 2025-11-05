import keysight_ktm5200x
import numpy as np
from time import sleep
import psutil, socket
import Pyro4
import Pyro4.naming

m5200_visa_addr = "PXI0::12-0.0::INSTR"

idQuery = False
reset   = False
options = "Simulate=False"

def start_nameserver(ns_host='127.0.0.1', ns_port=8888):
    """Starts a Pyro4 nameserver.

    Parameters
    ----------
    ns_host : str
        the nameserver hostname
    ns_port : int
        the port number for the nameserver to listen on

    Returns
    -------
    """
    Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle'])
    Pyro4.config.PICKLE_PROTOCOL_VERSION=4
    Pyro4.naming.startNSloop(host=ns_host, port=ns_port)

class M5200_Wrapper:
    def __init__(self, dev):
        self.dev = dev
    
    def fetch_waveform_int16(self, buffer, number_of_samples) -> None:
        self.dev.fetch_waveform_int16(buffer, number_of_samples)
    
    def daq_flush(self) -> None:
        self.dev.daq_flush()
    
    def daq_start(self) -> None:
        self.dev.daq_start()
    
    def set_daq_config(self, number_of_samples) -> None:
        self.dev.set_daq_config(
            1,
            number_of_samples,
            keysight_ktm5200x.TriggerMode.HW_DIG_TRIG,
            0
        )
        self.dev.external_trigger_config(
            keysight_ktm5200x.TriggerSource.SMB_TRIG1,
            keysight_ktm5200x.ExternalTriggerMode.RISING_EDGE,
            keysight_ktm5200x.SyncMode.IMMEDIATE
        )
    
    @property
    def daq_counter(self) -> int:
        return self.dev.daq_counter

if __name__ == "__main__":
    digitizer = keysight_ktm5200x.KtM5200x(
        m5200_visa_addr,
        idQuery,
        reset,
        options
    )
    ns_host = "127.0.0.1"
    ns_port = 8888
    proxy_name="digitizer_0"

    print("Digitizer Initialized")

    print(" identifier: ",  digitizer.identity.identifier)
    print(" revision: ",    digitizer.identity.revision)
    print(" vendor: ",      digitizer.identity.vendor)
    print(" description:",  digitizer.identity.description)
    print(" model: ",       digitizer.identity.instrument_model)
    print(" resource: ",    digitizer.driver_operation.io_resource_descriptor)
    print(" options: ",     digitizer.system.options)
    print(" simulate: ",    digitizer.driver_operation.simulate)

    print("Digitizer Connection is completed")

    try:
        Pyro4.config.REQUIRE_EXPOSE = False
        Pyro4.config.SERIALIZER = "pickle"
        Pyro4.config.SERIALIZERS_ACCEPTED=set(['pickle'])
        Pyro4.config.PICKLE_PROTOCOL_VERSION=4

        print("looking for nameserver . . .")
        ns = Pyro4.locateNS(host=ns_host, port=ns_port)
        print("found nameserver")

        # if we have multiple network interfaces, we want to register the daemon using the IP address that faces the nameserver
        host = Pyro4.socketutil.getInterfaceAddress(ns._pyroUri.host)
        daemon = Pyro4.Daemon(host=host)

        # if you want to use a different firmware image or set some initialization options, you would do that here
        ns.register(
            "digitizer_0",
            daemon.register(
                M5200_Wrapper(digitizer.channels[0])
            )
        )
        ns.register(
            "digitizer_1",
            daemon.register(
                M5200_Wrapper(digitizer.channels[1])
            )
        )
        print("starting daemon")
        daemon.requestLoop() # this will run forever until interrupted
    except:
        raise Exception("Exception has been occured...")
    finally:
        digitizer.close()

