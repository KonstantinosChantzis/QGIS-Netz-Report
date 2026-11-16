def classFactory(iface):
    from .netz_report import NetzReportPlugin
    return NetzReportPlugin(iface)
