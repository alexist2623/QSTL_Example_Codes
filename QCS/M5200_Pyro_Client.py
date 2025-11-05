import psutil, socket
import Pyro4
import Pyro4.naming

def make_proxy(ns_host, ns_port=8888, proxy_name='digitizer_0', remote_traceback=True):
    """Connects to a QickSoc proxy server.

    Parameters
    ----------
    ns_host : str
        hostname or IP address of the nameserver
        if the nameserver is running on the same PC you are running make_proxy() on, "localhost" is fine
    ns_port : int
        the port number you used when starting the nameserver
    proxy_name : str
        name for the QickSoc proxy you used when running start_server()
    remote_traceback : bool
        if running in IPython (Jupyter etc.), reconfigure the IPython exception handler to print the remote Pyro traceback

    Returns
    -------
    Proxy
        proxy to QickSoc - this is usually called "soc" in demos
    QickConfig
        config object - this is usually called "soccfg" in demos
    """
    Pyro4.config.SERIALIZER = "pickle"
    Pyro4.config.PICKLE_PROTOCOL_VERSION=4

    ns = Pyro4.locateNS(host=ns_host, port=ns_port)

    # print the nameserver entries: you should see the QickSoc proxy
    for k,v in ns.list().items():
        print(k,v)

    dig = Pyro4.Proxy(ns.lookup(proxy_name))

    # adapted from https://pyro4.readthedocs.io/en/stable/errors.html and https://stackoverflow.com/a/70433500
    if remote_traceback:
        try:
            import IPython
            import sys
            ip = IPython.get_ipython()
            if ip is not None:
                def exception_handler(self, etype, evalue, tb, tb_offset=None):
                    sys.stderr.write("".join(Pyro4.util.getPyroTraceback()))
                    # self.showtraceback((etype, evalue, tb), tb_offset=tb_offset)  # standard IPython's printout
                ip.set_custom_exc((Exception,), exception_handler)  # register your handler
        except Exception as e:
            raise RuntimeError("Failed to set up Pyro exception handler: ", e)

    return dig

if __name__ == "__main__":
    dig = make_proxy(
        ns_host = "192.168.19.2",
        ns_port = 8888,
        proxy_name='digitizer_0'
    )
    dig.set_daq_config(4200)
    dig.daq_flush()
