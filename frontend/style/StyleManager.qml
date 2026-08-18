pragma Singleton
import QtQuick

QtObject {
    id: style

    readonly property var fallbackStyle: ({
        id: "gt_modern",
        label: "GT moderne",
        description: "Style de secours CliOS GT",
        dashboard: "styles/gt_modern/Dashboard.qml",
        palette: {
            background: "#080B0F", surface: "#11171D", surfaceRaised: "#182029",
            surfaceSoft: "#202A34", text: "#F4F7FA", textSecondary: "#CDD5DD",
            outline: "#34414D", gaugeTrack: "#27323D"
        },
        metrics: { radiusSmall: 8, radiusMedium: 14, radiusLarge: 20, borderWidth: 1 }
    })
    readonly property var styles: {
        const discovered = bridge.getAvailableUiStyles()
        return discovered && discovered.length ? discovered : [fallbackStyle]
    }
    property string styleId: {
        const cfg = bridge && bridge.config ? bridge.config : ({})
        const requested = cfg.ui && cfg.ui.visual_style ? cfg.ui.visual_style : "gt_modern"
        return styleById(requested) ? requested : "gt_modern"
    }
    readonly property var current: styleById(styleId) || fallbackStyle
    readonly property var palette: current.palette || fallbackStyle.palette
    readonly property var metrics: current.metrics || ({})
    readonly property string dashboardSource: current.dashboard || fallbackStyle.dashboard

    readonly property color background: palette.background
    readonly property color surface: palette.surface
    readonly property color surfaceRaised: palette.surfaceRaised
    readonly property color surfaceSoft: palette.surfaceSoft
    readonly property color text: palette.text
    readonly property color textSecondary: palette.textSecondary
    readonly property color outline: palette.outline
    readonly property color gaugeTrack: palette.gaugeTrack

    readonly property color danger: "#FF4D5A"
    readonly property color warning: "#FFB33B"
    readonly property color success: "#4DDB8A"
    readonly property color info: "#61B8FF"
    readonly property color accent: readableAccent(rawAccent)
    readonly property color accentSoft: Qt.rgba(accent.r, accent.g, accent.b, 0.18)
    readonly property color rawAccent: {
        const cfg = bridge && bridge.config ? bridge.config : ({})
        return cfg.theme && cfg.theme.main ? cfg.theme.main : "#48B8FF"
    }

    readonly property string fontFamily: "Arial"
    readonly property int radiusSmall: Number(metrics.radiusSmall !== undefined ? metrics.radiusSmall : 8)
    readonly property int radiusMedium: Number(metrics.radiusMedium !== undefined ? metrics.radiusMedium : 14)
    readonly property int radiusLarge: Number(metrics.radiusLarge !== undefined ? metrics.radiusLarge : 20)
    readonly property int borderWidth: Number(metrics.borderWidth !== undefined ? metrics.borderWidth : 1)
    readonly property int spacingXs: 6
    readonly property int spacingSm: 10
    readonly property int spacingMd: 16
    readonly property int spacingLg: 24
    readonly property int durationFast: 120
    readonly property int durationNormal: 180
    readonly property int durationSlow: 250

    function styleById(id) {
        for (let i = 0; i < styles.length; ++i) {
            if (styles[i].id === id)
                return styles[i]
        }
        return null
    }

    function readableAccent(value) {
        const c = Qt.color(value || "#48B8FF")
        return Qt.hsva(c.hsvHue < 0 ? 0.55 : c.hsvHue,
                       Math.max(0.38, c.hsvSaturation),
                       Math.max(0.66, c.hsvValue), 1.0)
    }

    function selectStyle(id) {
        if (!styleById(id) || id === styleId)
            return
        bridge.save_setting("ui.visual_style", id)
    }
}
