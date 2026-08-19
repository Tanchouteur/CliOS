pragma Singleton
import QtQuick

QtObject {
    id: state

    // =========================================================================
    // 1. SOURCES BRUTES SÉCURISÉES DEPUIS LE BRIDGE PYTHON
    // =========================================================================
    readonly property var vehicle: bridge && bridge.data ? bridge.data : ({})
    readonly property var trip: bridge && bridge.stats ? bridge.stats : ({})
    readonly property var health: bridge && bridge.systemHealth ? bridge.systemHealth : ({})
    readonly property var storage: bridge && bridge.storageStatus ? bridge.storageStatus : ({})
    readonly property var config: bridge && bridge.config ? bridge.config : ({})

    // =========================================================================
    // 2. CONFIGURATION DU VÉHICULE & CALIBRATIONS
    // =========================================================================
    readonly property real maxSpeed: number(config.speedometer && config.speedometer.max_speed, 250)
    readonly property real maxRpm: number(config.tachometer && config.tachometer.max_rpm, 7000)
    readonly property real redlineRpm: number(config.tachometer && config.tachometer.redline_rpm, 6500)
    readonly property real idleRpm: number(config.tachometer && config.tachometer.idle_rpm, 850)
    readonly property real maxFuel: number(config.fuel && config.fuel.max_liters, 55)
    readonly property real reservePercentage: number(config.fuel && config.fuel.reserve_percentage, 0.15)
    readonly property real tempMin: number(config.engine_temp && config.engine_temp.min_display, 40)
    readonly property real tempOptimal: number(config.engine_temp && config.engine_temp.optimal, 90)
    readonly property real tempWarning: number(config.engine_temp && config.engine_temp.warning, 105)
    readonly property real tempMax: number(config.engine_temp && config.engine_temp.max_display, 120)
    readonly property real instantConsMax: number(config.instant_fuel_consumption && config.instant_fuel_consumption.max_display, 20.0)
    readonly property real revisionIntervalKm: number(config.maintenance && config.maintenance.revision && config.maintenance.revision.interval_km, 20000)
    readonly property real revisionWarningKm: number(config.maintenance && config.maintenance.revision && config.maintenance.revision.warning_threshold_km, 2000)

    // =========================================================================
    // 3. MÉTROLOGIE MOTEUR, VITESSE & TRANSMISSION
    // =========================================================================
    readonly property real speed: number(vehicle.speed, 0)
    readonly property real rpm: number(vehicle.rpm, 0)
    readonly property string gear: text(vehicle.gear, "N")
    readonly property real engineTemp: number(vehicle.engine_temp, 0)
    readonly property real outsideTemp: number(vehicle.outside_temp, 0)
    readonly property real fuelLevel: number(vehicle.fuel_level, 0)
    readonly property real odometer: number(vehicle.odometer, 0)
    readonly property string sessionState: text(vehicle.session_state, "IDLE")

    // Pédales & Couple
    readonly property real throttle: number(vehicle.throttle !== undefined ? vehicle.throttle : (vehicle.accel_pos !== undefined ? vehicle.accel_pos : (vehicle.throttle_pct !== undefined ? vehicle.throttle_pct : 0)), 0)
    readonly property real pedalPos: throttle
    readonly property real accelComputed: number(vehicle.accel_computed, 0)
    readonly property real driverTorqueRequest: number(vehicle.driver_torque_request, 0)
    readonly property real torqueAvailable: number(vehicle.torque_available, 0)
    readonly property real torque: number(vehicle.torque !== undefined ? vehicle.torque : (vehicle.torque_nm !== undefined ? vehicle.torque_nm : driverTorqueRequest), 0)
    readonly property real power: number(vehicle.power !== undefined ? vehicle.power : (vehicle.power_kw !== undefined ? vehicle.power_kw : (rpm > 0 && driverTorqueRequest ? (rpm * driverTorqueRequest / 9549) : 0)), 0)

    // État mécanique
    readonly property bool brakePressed: boolValue(vehicle.brake) || boolValue(vehicle.brake_pressed)
    readonly property bool clutchPressed: boolValue(vehicle.clutch)
    readonly property bool handbrakeActive: boolValue(vehicle.parking_brake) || boolValue(vehicle.handbrake) || boolValue(vehicle.handbrake_status)
    readonly property bool reverseEngaged: boolValue(vehicle.reverse_engaged) || boolValue(vehicle.reverse) || gear === "R"
    readonly property string engineLight: text(vehicle.engine_light, "OFF") // "RED", "ORANGE", "OFF"
    readonly property bool glowPlugActive: boolValue(vehicle.glow_plug_status)

    // Alertes d'état moteur
    readonly property bool lowFuel: maxFuel > 0 && fuelLevel / maxFuel <= reservePercentage
    readonly property bool hotEngine: engineTemp >= tempWarning
    readonly property bool redline: rpm >= redlineRpm

    // =========================================================================
    // 4. RÉGULATEUR & LIMITEUR DE VITESSE
    // =========================================================================
    readonly property string cruiseMode: cruiseModeLabel(vehicle.regulateur_mode)
    readonly property string cruiseStatus: cruiseStatusLabel(vehicle.regulateur_statut)
    readonly property real cruiseTarget: number(vehicle.vitesse_regulateur, 0)

    // =========================================================================
    // 5. STATISTIQUES DE TRAJET & CONSOMMATION (TripStatsService)
    // =========================================================================
    readonly property bool tripActive: trip.is_active === true || sessionState === "RUNNING"
    readonly property real tripDistance: number(trip.distance_km, 0)
    readonly property real tripFuelLiters: number(trip.session_fuel_l, 0)
    readonly property real tripCost: number(trip.session_cost, 0)
    readonly property real fuelPrice: number(trip.fuel_price, 1.70)
    readonly property real avgRpm: number(trip.avg_rpm, 0)
    readonly property real coastingKm: number(trip.coasting_km, 0)
    readonly property real aggressivityPct: number(trip.aggressivity_pct, 0)
    readonly property real shiftTimeSec: number(trip.shift_time_sec, 0)
    readonly property real tripA: number(trip.trip_a, 0)
    readonly property real tripB: number(trip.trip_b, 0)
    readonly property real tripBFuel: number(trip.trip_b_fuel, 0)
    readonly property real instantCons: number(trip.inst_cons !== undefined ? trip.inst_cons : (vehicle.inst_cons !== undefined ? vehicle.inst_cons : 0), 0)
    readonly property real avgConsB: number(trip.avg_cons_b, 0)
    readonly property real avgConsSession: number(trip.avg_cons_session, 0)
    readonly property real autonomy: number(trip.autonomy, 0)
    readonly property real kmBeforeService: number(trip.km_before_service, 0)
    readonly property bool serviceWarning: boolValue(trip.service_warning)
    readonly property real gForce: number(trip.g_force !== undefined ? trip.g_force : 0, 0)

    // =========================================================================
    // 6. CHÂSSIS, ROUES & DYNAMIQUE (DynamicsService)
    // =========================================================================
    readonly property real wheelSpeedFl: number(vehicle.wheel_speed_fl !== undefined ? vehicle.wheel_speed_fl : vehicle.wheel_fl_speed, 0)
    readonly property real wheelSpeedFr: number(vehicle.wheel_speed_fr !== undefined ? vehicle.wheel_speed_fr : vehicle.wheel_fr_speed, 0)
    readonly property real wheelSpeedRl: number(vehicle.wheel_speed_rl !== undefined ? vehicle.wheel_speed_rl : vehicle.wheel_rl_speed, 0)
    readonly property real wheelSpeedRr: number(vehicle.wheel_speed_rr !== undefined ? vehicle.wheel_speed_rr : vehicle.wheel_rr_speed, 0)

    readonly property bool wheelSlipFl: boolValue(vehicle.wheel_slip_fl)
    readonly property bool wheelSlipFr: boolValue(vehicle.wheel_slip_fr)
    readonly property bool wheelSlipRl: boolValue(vehicle.wheel_slip_rl)
    readonly property bool wheelSlipRr: boolValue(vehicle.wheel_slip_rr)
    readonly property bool hasWheelSlip: wheelSlipFl || wheelSlipFr || wheelSlipRl || wheelSlipRr

    readonly property bool wheelLockFl: boolValue(vehicle.wheel_lock_fl)
    readonly property bool wheelLockFr: boolValue(vehicle.wheel_lock_fr)
    readonly property bool wheelLockRl: boolValue(vehicle.wheel_lock_rl)
    readonly property bool wheelLockRr: boolValue(vehicle.wheel_lock_rr)
    readonly property bool hasWheelLock: wheelLockFl || wheelLockFr || wheelLockRl || wheelLockRr

    readonly property real steeringAngle: number(vehicle.steering_angle, 0)
    readonly property real steeringSpeed: number(vehicle.steering_speed, 0)

    // =========================================================================
    // 7. CARROSSERIE, OUVRANTS & CONFORT
    // =========================================================================
    readonly property bool doorFlOpen: boolValue(vehicle.door_fl_open)
    readonly property bool doorFrOpen: boolValue(vehicle.door_fr_open)
    readonly property bool doorRlOpen: boolValue(vehicle.door_rl_open)
    readonly property bool doorRrOpen: boolValue(vehicle.door_rr_open)
    readonly property bool trunkOpen: boolValue(vehicle.trunk_open)
    readonly property bool doorOpen: doorFlOpen || doorFrOpen || doorRlOpen || doorRrOpen || trunkOpen

    readonly property bool doorsLocked: boolValue(vehicle.doors_locked)
    readonly property bool trunkLocked: boolValue(vehicle.trunk_locked)
    readonly property bool driverUnbelted: boolValue(vehicle.driver_unbelted)
    readonly property bool passengerAirbagDisabled: boolValue(vehicle.passenger_disabled)
    readonly property bool attentionVehicle: driverUnbelted || doorOpen

    // Éclairage
    readonly property bool lightsActive: boolValue(vehicle.lights) || boolValue(vehicle.pos_lights) || boolValue(vehicle.low_beam)
    readonly property bool highBeamActive: boolValue(vehicle.high_beam)
    readonly property bool fogFrontActive: boolValue(vehicle.fog_front)
    readonly property bool fogRearActive: boolValue(vehicle.fog_rear)
    readonly property bool turnLeftActive: boolValue(vehicle.indicator_left) || boolValue(vehicle.turn_left)
    readonly property bool turnRightActive: boolValue(vehicle.indicator_right) || boolValue(vehicle.turn_right)
    readonly property real brightness: number(vehicle.brightness, 100)

    // =========================================================================
    // 8. ACOUSTIQUE HABITACLE & SURVEILLANCE SYSTÈME (Monitor / Noise / Storage)
    // =========================================================================
    readonly property real cabinDbSpl: number(vehicle.cabin_db_spl !== undefined ? vehicle.cabin_db_spl : vehicle.cabin_noise_db, 0)
    readonly property int cabinFreqHz: intValue(vehicle.cabin_freq_hz, 0)
    readonly property real appCpuTotalPct: number(vehicle.app_cpu_total_pct, 0)
    readonly property real appRamMb: number(vehicle.app_ram_mb, 0)

    readonly property bool usbConnected: storage.usb_connected === true
    readonly property bool ramMode: !usbConnected || storage.mode === "RAM"
    readonly property real storageFreeMb: number(storage.free_space_mb, 0)
    readonly property string storageMode: text(storage.mode, "UNKNOWN")

    // Diagnostic OBD
    readonly property bool isScanning: bridge && bridge.isScanning === true
    readonly property bool hasScanned: bridge && bridge.hasScanned === true
    readonly property var diagnosticCodes: bridge && bridge.diagnosticCodes ? bridge.diagnosticCodes : []

    // Services
    readonly property var serviceErrorKeys: serviceKeys("ERROR")
    readonly property var serviceWarningKeys: serviceKeys("WARNING")
    readonly property bool complexInteraction: speed > 5

    // =========================================================================
    // 9. TABLEAU UNIVERSEL DES VOYANTS DU COMBINÉ
    // =========================================================================
    readonly property var indicators: [
        { code: "G", label: "Clignotant gauche", active: turnLeftActive, color: "#4DDB8A", blink: true },
        { code: "D", label: "Clignotant droit", active: turnRightActive, color: "#4DDB8A", blink: true },
        { code: "FEU", label: "Feux", active: lightsActive || highBeamActive || fogFrontActive || fogRearActive, color: "#4DDB8A", blink: false },
        { code: "STOP", label: "Frein", active: handbrakeActive || boolValue(vehicle.brake_warning) || boolValue(vehicle.stop_warning), color: "#FF4D5A", blink: false },
        { code: "CEINT", label: "Ceinture", active: driverUnbelted, color: "#FF4D5A", blink: false },
        { code: "PORTE", label: "Porte", active: doorOpen, color: "#FFB33B", blink: false },
        { code: "HUILE", label: "Huile", active: boolValue(vehicle.oil_warning), color: "#FF4D5A", blink: false },
        { code: "BAT", label: "Batterie", active: boolValue(vehicle.battery_warning), color: "#FF4D5A", blink: false },
        { code: "ABS", label: "ABS", active: boolValue(vehicle.abs_warning) || boolValue(vehicle.abs_error) || hasWheelLock, color: "#FFB33B", blink: false },
        { code: "ESP", label: "ESP", active: boolValue(vehicle.esp_warning) || boolValue(vehicle.esp_active) || hasWheelSlip, color: "#FFB33B", blink: false },
        { code: "MOT", label: "Moteur", active: boolValue(vehicle.engine_warning) || engineLight !== "OFF", color: "#FFB33B", blink: false }
    ]

    // =========================================================================
    // 10. FONCTIONS UTILITAIRES DE CONVERSION & SÉCURISATION
    // =========================================================================
    function number(value, fallback) {
        const parsed = Number(value)
        return isFinite(parsed) ? parsed : fallback
    }

    function intValue(value, fallback) {
        const parsed = parseInt(value, 10)
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
        if (!health) return []
        const keys = Object.keys(health)
        return keys.filter(function(key) {
            return health[key] && health[key].status === status
        })
    }

    function profileName() {
        if (!bridge || typeof bridge.getActiveProfile !== "function") return "CliOS"
        const id = bridge.getActiveProfile()
        const profiles = typeof bridge.getAvailableProfiles === "function" ? bridge.getAvailableProfiles() : []
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
