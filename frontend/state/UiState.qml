pragma Singleton
import QtQuick

QtObject {
    id: state

    readonly property var vehicle: bridge && bridge.data ? bridge.data : ({})
    readonly property var trip: bridge && bridge.stats ? bridge.stats : ({})
    readonly property var health: bridge && bridge.systemHealth ? bridge.systemHealth : ({})
    readonly property var storage: bridge && bridge.storageStatus ? bridge.storageStatus : ({})
    readonly property var config: bridge && bridge.config ? bridge.config : ({})

    readonly property real speed: number(vehicle.speed, 0)
    readonly property real rpm: number(vehicle.rpm, 0)
    readonly property string gear: text(vehicle.gear, "N")
    readonly property real engineTemp: number(vehicle.engine_temp, 0)
    readonly property real outsideTemp: number(vehicle.outside_temp, 0)
    readonly property real fuelLevel: number(vehicle.fuel_level, 0)
    readonly property real odometer: number(vehicle.odometer, 0)
    readonly property string sessionState: text(vehicle.session_state, "IDLE")
    readonly property bool tripActive: trip.is_active === true || sessionState === "RUNNING"
    readonly property bool complexInteraction: speed > 5

    readonly property string cruiseMode: cruiseModeLabel(vehicle.regulateur_mode)
    readonly property string cruiseStatus: cruiseStatusLabel(vehicle.regulateur_statut)
    readonly property real cruiseTarget: number(vehicle.vitesse_regulateur, 0)
    readonly property real maxRpm: number(config.tachometer && config.tachometer.max_rpm, 7000)
    readonly property real redlineRpm: number(config.tachometer && config.tachometer.redline_rpm, 6500)
    readonly property real maxFuel: number(config.fuel && config.fuel.max_liters, 55)
    readonly property real tempWarning: number(config.engine_temp && config.engine_temp.warning, 105)
    readonly property real tempMax: number(config.engine_temp && config.engine_temp.max_display, 120)

    readonly property bool lowFuel: maxFuel > 0 && fuelLevel / maxFuel <= 0.15
    readonly property bool hotEngine: engineTemp >= tempWarning
    readonly property bool redline: rpm >= redlineRpm
    readonly property bool doorOpen: boolValue(vehicle.trunk_open) || boolValue(vehicle.door_fl_open)
                                     || boolValue(vehicle.door_fr_open) || boolValue(vehicle.door_rl_open)
                                     || boolValue(vehicle.door_rr_open)
    readonly property bool attentionVehicle: boolValue(vehicle.driver_unbelted) || doorOpen

    readonly property var serviceErrorKeys: serviceKeys("ERROR")
    readonly property var serviceWarningKeys: serviceKeys("WARNING")
    readonly property bool usbConnected: storage.usb_connected === true
    readonly property bool ramMode: !usbConnected || storage.mode === "RAM"

    readonly property var indicators: [
        { code: "G", label: "Clignotant gauche", active: boolValue(vehicle.indicator_left) || boolValue(vehicle.turn_left), color: "#4DDB8A", blink: true },
        { code: "D", label: "Clignotant droit", active: boolValue(vehicle.indicator_right) || boolValue(vehicle.turn_right), color: "#4DDB8A", blink: true },
        { code: "FEU", label: "Feux", active: boolValue(vehicle.lights) || boolValue(vehicle.pos_lights) || boolValue(vehicle.low_beam) || boolValue(vehicle.high_beam) || boolValue(vehicle.fog_front) || boolValue(vehicle.fog_rear), color: "#4DDB8A", blink: false },
        { code: "STOP", label: "Frein", active: boolValue(vehicle.parking_brake) || boolValue(vehicle.brake_warning), color: "#FF4D5A", blink: false },
        { code: "CEINT", label: "Ceinture", active: boolValue(vehicle.driver_unbelted), color: "#FF4D5A", blink: false },
        { code: "PORTE", label: "Porte", active: attentionVehicle && !boolValue(vehicle.driver_unbelted), color: "#FFB33B", blink: false },
        { code: "HUILE", label: "Huile", active: boolValue(vehicle.oil_warning), color: "#FF4D5A", blink: false },
        { code: "BAT", label: "Batterie", active: boolValue(vehicle.battery_warning), color: "#FF4D5A", blink: false },
        { code: "ABS", label: "ABS", active: boolValue(vehicle.abs_warning), color: "#FFB33B", blink: false },
        { code: "ESP", label: "ESP", active: boolValue(vehicle.esp_warning), color: "#FFB33B", blink: false },
        { code: "MOT", label: "Moteur", active: boolValue(vehicle.engine_warning), color: "#FFB33B", blink: false }
    ]

    function number(value, fallback) {
        const parsed = Number(value)
        return isFinite(parsed) ? parsed : fallback
    }

    function text(value, fallback) {
        return value === undefined || value === null || value === "" ? fallback : String(value)
    }

    function boolValue(value) {
        return value === true || value === 1 || value === "1" || value === "true"
    }

    function cruiseModeLabel(value) {
        if (value === "REG" || Number(value) === 2) return "REG"
        if (value === "LIM" || Number(value) === 3) return "LIM"
        return "OFF"
    }

    function cruiseStatusLabel(value) {
        if (value === "ACTIF" || Number(value) === 4) return "ACTIF"
        return "INACTIF"
    }

    function fixed(value, decimals, fallback) {
        const parsed = Number(value)
        return isFinite(parsed) ? parsed.toFixed(decimals) : (fallback || "—")
    }

    function serviceKeys(status) {
        const keys = Object.keys(health)
        return keys.filter(function(key) {
            return health[key] && health[key].status === status
        })
    }

    function profileName() {
        const id = bridge.getActiveProfile()
        const profiles = bridge.getAvailableProfiles()
        for (let i = 0; i < profiles.length; ++i) {
            const p = profiles[i]
            if (typeof p === "object" && (p.id === id || p.profile_id === id))
                return p.name || id
            if (String(p) === id)
                return id
        }
        return id || "CliOS"
    }
}
