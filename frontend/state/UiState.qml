pragma Singleton
import QtQuick

QtObject {
    id: state

    // =========================================================================
    // 1. SOURCES BRUTES SÉCURISÉES DEPUIS LE BRIDGE PYTHON
    // =========================================================================
    readonly property var vehicleState: bridge && bridge.vehicleState ? bridge.vehicleState : ({})
    readonly property var rawTripState: bridge && bridge.tripState ? bridge.tripState : ({})
    readonly property var diagnosticsState: bridge && bridge.diagnosticsState ? bridge.diagnosticsState : ({})
    readonly property var sessionRuntimeState: bridge && bridge.sessionState ? bridge.sessionState : ({})
    readonly property var calibrationState: bridge && bridge.calibrationState ? bridge.calibrationState : ({})
    readonly property var systemState: bridge && bridge.systemState ? bridge.systemState : ({})
    readonly property var presentationState: bridge && bridge.presentationState ? bridge.presentationState : ({})
    readonly property var dataQuality: bridge && bridge.dataQuality ? bridge.dataQuality : ({})
    readonly property var config: bridge && bridge.config ? bridge.config : ({})

    readonly property var powertrain: presentedDomain("powertrain")
    readonly property var motion: presentedDomain("motion")
    readonly property var wheels: presentedDomain("wheels")
    readonly property var body: presentedDomain("body")
    readonly property var assistance: presentedDomain("assistance")
    readonly property var dynamics: presentedDomain("dynamics")
    readonly property var environment: presentedDomain("environment")
    readonly property var alerts: presentedDomain("alerts")
    readonly property var tripState: presentedStandaloneDomain("trip", rawTripState)
    readonly property var serviceHealth: systemState.health || ({})
    readonly property var storageState: systemState.storage || ({})
    readonly property var telemetryState: systemState.telemetry || ({})
    readonly property var updaterState: systemState.updater || ({
        "state": "IDLE", "installed_version": systemVersion, "available_version": "",
        "channel": "stable", "progress": 0, "message": "", "can_activate": false,
        "can_rollback": false, "rollback_target": "", "phase": "idle", "detail": "",
        "started_at": 0, "updated_at": 0, "last_manifest": ({}), "error": ({}),
        "helper_error": ({})
    })
    readonly property var ledDevices: systemState.led_devices || []
    readonly property var ledGroups: systemState.led_groups || []
    readonly property int ledMaxDevices: number(systemState.led_max_devices, 4)
    readonly property bool bleScanning: systemState.ble_scanning === true
    readonly property var bleScanResults: systemState.ble_scan_results || []
    readonly property var bleCharacteristics: systemState.ble_characteristics || []
    readonly property var bleTestState: systemState.ble_test_state || ({})

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
    readonly property string engineLabel: text(config.engine && config.engine.label, "Moteur")
    readonly property real maxPowerKw: number(config.engine && config.engine.max_power_kw, 100)
    readonly property real maxPowerHp: maxPowerKw * 1.359621617
    readonly property real maxPowerRpm: number(config.engine && config.engine.max_power_rpm, maxRpm * 0.8)
    readonly property real maxTorqueNm: number(config.engine && config.engine.max_torque_nm, 200)
    readonly property real maxTorqueRpm: number(config.engine && config.engine.max_torque_rpm, maxRpm * 0.45)
    readonly property var engineCurve: config.engine && config.engine.performance_curve ? config.engine.performance_curve : []
    readonly property real revisionIntervalKm: number(config.maintenance && config.maintenance.revision && config.maintenance.revision.interval_km, 20000)
    readonly property real revisionWarningKm: number(config.maintenance && config.maintenance.revision && config.maintenance.revision.warning_threshold_km, 2000)

    // Transmission & Boîte de vitesses
    readonly property var transmissionConfig: config.transmission || ({})
    readonly property var gearRatios: transmissionConfig.ratios || ({})
    readonly property string transmissionType: {
        const t = text(transmissionConfig.type, "").toLowerCase()
        if (t === "auto" || t === "bva" || t === "automatic" || t === "automatique") return "auto"
        if (t === "manual" || t === "manuelle" || t === "mecanique" || t === "bvm") return "manual"
        const rKeys = Object.keys(gearRatios)
        if (rKeys.length > 0) return "manual"
        if (gear === "P" || gear === "D" || gear === "D3") return "auto"
        return "manual"
    }
    readonly property bool isManualGearbox: transmissionType === "manual"
    readonly property bool isAutomaticGearbox: transmissionType === "auto"
    readonly property int manualGearCount: {
        if (transmissionConfig.gears_count !== undefined && Number(transmissionConfig.gears_count) > 0)
            return Number(transmissionConfig.gears_count)
        if (transmissionConfig.gears !== undefined && Number(transmissionConfig.gears) > 0)
            return Number(transmissionConfig.gears)
        const keys = Object.keys(gearRatios).map(k => parseInt(k, 10)).filter(n => !isNaN(n) && n > 0)
        if (keys.length > 0)
            return Math.max(...keys)
        return 5
    }

    // Signaux bruts d'entrée
    readonly property real rawSpeed: signalFresh("motion", "speed") ? number(motion.speed, 0) : 0
    readonly property real rawRpm: signalFresh("powertrain", "rpm") ? number(powertrain.rpm, 0) : 0
    readonly property real rawEngineTemp: number(powertrain.engine_temp, 0)
    readonly property real rawOutsideTemp: number(environment.outside_temp, 0)
    readonly property real rawFuelLevel: number(powertrain.fuel_level, 0)
    readonly property real rawThrottle: number(powertrain.accel_pos, 0)
    readonly property real rawDriverTorqueRequest: number(powertrain.driver_torque_request, 0)
    readonly property real rawEcuTorqueAvailablePct: number(powertrain.torque_available, 0)
    readonly property real rawEngineLoad: number(powertrain.engine_load_pct, 0)
    readonly property real rawAvailableTorque: number(powertrain.available_torque_nm, maxTorqueNm)
    readonly property real rawEstimatedTorque: number(powertrain.estimated_torque_nm, 0)
    readonly property real rawPower: number(powertrain.estimated_power_kw, 0)
    readonly property real rawPowerHp: number(powertrain.estimated_power_hp, 0)
    readonly property real rawInstantCons: number(tripState.inst_cons, 0)
    readonly property real rawCabinDbSpl: number(environment.cabin_db_spl, 0)
    readonly property real rawLongitudinalG: number(tripState.longitudinal_g, 0)
    readonly property real rawSteeringAngle: number(dynamics.steering_angle, 0)
    readonly property real rawSteeringSpeed: number(dynamics.steering_speed, 0)
    readonly property real rawWheelSpeedFl: number(wheels.wheel_fl_speed, 0)
    readonly property real rawWheelSpeedFr: number(wheels.wheel_fr_speed, 0)
    readonly property real rawWheelSpeedRl: number(wheels.wheel_rl_speed, 0)
    readonly property real rawWheelSpeedRr: number(wheels.wheel_rr_speed, 0)

    // =========================================================================
    // 3. MÉTROLOGIE MOTEUR, VITESSE & TRANSMISSION
    // =========================================================================
    property real speed: rawSpeed
    readonly property real rpm: rawRpm
    readonly property string gear: text(motion.gear, "N")
    property real engineTemp: rawEngineTemp
    property real outsideTemp: rawOutsideTemp
    property real fuelLevel: rawFuelLevel
    readonly property real odometer: number(motion.odometer, 0)
    readonly property string sessionState: text(sessionRuntimeState.state, "IDLE")

    // Pédales & Couple
    property real throttle: rawThrottle
    property real pedalPos: throttle
    readonly property real accelComputed: number(powertrain.accel_computed, 0)
    property real driverTorqueRequest: rawDriverTorqueRequest
    property real ecuTorqueAvailablePct: rawEcuTorqueAvailablePct
    property real engineLoad: rawEngineLoad
    property real availableTorque: rawAvailableTorque
    property real estimatedTorque: rawEstimatedTorque
    property real torque: estimatedTorque
    property real power: rawPower
    property real powerHp: rawPowerHp

    // Lissage temporel adapté à l'inertie de chaque grandeur physique
    Behavior on speed { NumberAnimation { duration: 90; easing.type: Easing.OutQuad } }
    Behavior on engineTemp { NumberAnimation { duration: 700; easing.type: Easing.OutCubic } }
    Behavior on outsideTemp { NumberAnimation { duration: 900; easing.type: Easing.OutCubic } }
    Behavior on fuelLevel { NumberAnimation { duration: 1200; easing.type: Easing.OutCubic } }
    Behavior on throttle { NumberAnimation { duration: 60; easing.type: Easing.OutQuad } }
    Behavior on driverTorqueRequest { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
    Behavior on engineLoad { NumberAnimation { duration: 120; easing.type: Easing.OutQuad } }
    Behavior on estimatedTorque { NumberAnimation { duration: 100; easing.type: Easing.OutQuad } }
    Behavior on power { NumberAnimation { duration: 100; easing.type: Easing.OutQuad } }
    Behavior on powerHp { NumberAnimation { duration: 100; easing.type: Easing.OutQuad } }

    // État mécanique
    readonly property bool brakePressed: boolValue(motion.brake) || boolValue(motion.brake_pressed)
    readonly property bool clutchPressed: boolValue(motion.clutch)
    readonly property bool handbrakeActive: boolValue(motion.handbrake)
    readonly property bool reverseEngaged: boolValue(motion.reverse) || boolValue(motion.reverse_engaged) || gear === "R"
    readonly property string engineLight: text(alerts.engine_light, "OFF")
    readonly property bool glowPlugActive: boolValue(powertrain.glow_plug_status)
    readonly property bool ignitionOn: boolValue(powertrain.key_run)

    // Alertes d'état moteur
    readonly property bool lowFuel: boolValue(alerts.low_fuel)
    readonly property bool hotEngine: boolValue(alerts.hot_engine)
    readonly property bool redline: boolValue(alerts.redline)
    readonly property bool brakeWarning: boolValue(alerts.brake_warning) || boolValue(alerts.stop_warning)
    readonly property bool oilWarning: boolValue(alerts.oil_warning)
    readonly property bool batteryWarning: boolValue(alerts.battery_warning)
    readonly property bool absWarning: boolValue(alerts.abs_warning) || boolValue(alerts.abs_error) || hasWheelLock
    readonly property bool espWarning: boolValue(alerts.esp_warning) || boolValue(alerts.esp_active) || hasWheelSlip
    readonly property bool engineWarning: boolValue(alerts.engine_warning) || engineLight !== "OFF"

    // =========================================================================
    // 4. RÉGULATEUR & LIMITEUR DE VITESSE
    // =========================================================================
    readonly property string cruiseMode: cruiseModeLabel(assistance.regulateur_mode)
    readonly property string cruiseStatus: cruiseStatusLabel(assistance.regulateur_statut)
    readonly property real cruiseTarget: number(assistance.vitesse_regulateur, 0)

    // =========================================================================
    // 5. STATISTIQUES DE TRAJET & CONSOMMATION (TripStatsService)
    // =========================================================================
    readonly property bool tripActive: tripState.is_active === true || sessionState === "RUNNING"
    readonly property real tripDistance: number(tripState.distance_km, 0)
    readonly property real tripFuelLiters: number(tripState.session_fuel_l, 0)
    readonly property real tripCost: number(tripState.session_cost, 0)
    readonly property real fuelPrice: number(tripState.fuel_price, 1.70)
    readonly property real avgRpm: number(tripState.avg_rpm, 0)
    readonly property real decelerationWithoutThrottleKm: number(tripState.deceleration_without_throttle_km, 0)
    readonly property real aggressivityPct: number(tripState.aggressivity_pct, 0)
    readonly property real shiftTimeSec: number(tripState.shift_time_sec, 0)
    readonly property real tripA: number(tripState.trip_a, 0)
    readonly property real tripB: number(tripState.trip_b, 0)
    readonly property real tripBFuel: number(tripState.trip_b_fuel, 0)
    property real instantCons: rawInstantCons
    readonly property real avgConsB: number(tripState.avg_cons_b, 0)
    readonly property real avgConsSession: number(tripState.avg_cons_session, 0)
    readonly property real autonomy: number(tripState.autonomy, 0)
    readonly property real kmBeforeService: number(tripState.km_before_service, 0)
    readonly property bool serviceWarning: boolValue(tripState.service_warning)
    property real longitudinalG: rawLongitudinalG

    Behavior on instantCons { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
    Behavior on longitudinalG { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

    // =========================================================================
    // 6. CHÂSSIS, ROUES & DYNAMIQUE (DynamicsService)
    // =========================================================================
    property real wheelSpeedFl: rawWheelSpeedFl
    property real wheelSpeedFr: rawWheelSpeedFr
    property real wheelSpeedRl: rawWheelSpeedRl
    property real wheelSpeedRr: rawWheelSpeedRr

    Behavior on wheelSpeedFl { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
    Behavior on wheelSpeedFr { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
    Behavior on wheelSpeedRl { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
    Behavior on wheelSpeedRr { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }

    readonly property bool wheelSlipFl: boolValue(wheels.wheel_slip_fl)
    readonly property bool wheelSlipFr: boolValue(wheels.wheel_slip_fr)
    readonly property bool wheelSlipRl: boolValue(wheels.wheel_slip_rl)
    readonly property bool wheelSlipRr: boolValue(wheels.wheel_slip_rr)
    readonly property bool hasWheelSlip: wheelSlipFl || wheelSlipFr || wheelSlipRl || wheelSlipRr

    readonly property bool wheelLockFl: boolValue(wheels.wheel_lock_fl)
    readonly property bool wheelLockFr: boolValue(wheels.wheel_lock_fr)
    readonly property bool wheelLockRl: boolValue(wheels.wheel_lock_rl)
    readonly property bool wheelLockRr: boolValue(wheels.wheel_lock_rr)
    readonly property bool hasWheelLock: wheelLockFl || wheelLockFr || wheelLockRl || wheelLockRr

    property real steeringAngle: rawSteeringAngle
    property real steeringSpeed: rawSteeringSpeed
    Behavior on steeringAngle { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }
    Behavior on steeringSpeed { NumberAnimation { duration: 80; easing.type: Easing.OutQuad } }

    // =========================================================================
    // 7. CARROSSERIE, OUVRANTS & CONFORT
    // =========================================================================
    readonly property bool doorFlOpen: boolValue(body.door_fl_open)
    readonly property bool doorFrOpen: boolValue(body.door_fr_open)
    readonly property bool doorRlOpen: boolValue(body.door_rl_open)
    readonly property bool doorRrOpen: boolValue(body.door_rr_open)
    readonly property bool trunkOpen: boolValue(body.trunk_open)
    readonly property bool doorOpen: doorFlOpen || doorFrOpen || doorRlOpen || doorRrOpen || trunkOpen

    readonly property bool doorsLocked: boolValue(body.doors_locked)
    readonly property bool trunkLocked: boolValue(body.trunk_locked)
    readonly property bool driverUnbelted: boolValue(body.driver_unbelted)
    readonly property bool passengerAirbagDisabled: boolValue(body.passenger_disabled)
    readonly property bool attentionVehicle: driverUnbelted || doorOpen

    // Éclairage
    readonly property bool lightsActive: boolValue(body.pos_lights) || boolValue(body.low_beam)
    readonly property bool highBeamActive: boolValue(body.high_beam)
    readonly property bool fogFrontActive: boolValue(body.fog_front)
    readonly property bool fogRearActive: boolValue(body.fog_rear)
    readonly property bool turnLeftActive: boolValue(body.turn_left)
    readonly property bool turnRightActive: boolValue(body.turn_right)
    readonly property real brightness: number(body.brightness, 100)

    // =========================================================================
    // 8. ACOUSTIQUE HABITACLE & SURVEILLANCE SYSTÈME (Monitor / Noise / Storage)
    // =========================================================================
    property real cabinDbSpl: rawCabinDbSpl
    Behavior on cabinDbSpl { NumberAnimation { duration: 250; easing.type: Easing.OutQuad } }
    readonly property int cabinFreqHz: intValue(environment.cabin_freq_hz, 0)
    readonly property real appCpuTotalPct: number(telemetryState.app_cpu_total_pct, 0)
    readonly property real appRamMb: number(telemetryState.app_ram_mb, 0)

    readonly property bool usbConnected: storageState.usb_connected === true
    readonly property bool ramMode: storageState.mode === "RAM"
    readonly property bool internalStorage: storageState.mode === "INTERNAL"
    readonly property real storageFreeMb: number(storageState.free_space_mb, 0)
    readonly property string storageMode: text(storageState.mode, "UNKNOWN")
    readonly property string storageMount: text(storageState.mount_point, "")
    readonly property string storageDiagnostic: text(storageState.usb_diagnostic, "")
    readonly property string systemVersion: text(systemState.version, "unknown")
    readonly property var recoveryState: systemState.recovery || ({})
    readonly property bool recoveryMode: recoveryState.active === true
    readonly property string recoveryMessage: text(recoveryState.message, "")

    // Diagnostic OBD
    readonly property bool isScanning: diagnosticsState.scanning === true
    readonly property bool hasScanned: diagnosticsState.has_scanned === true
    readonly property var diagnosticCodes: diagnosticsState.codes || []

    // Services
    readonly property var serviceErrorKeys: serviceKeys("ERROR")
    readonly property var serviceWarningKeys: serviceKeys("WARNING")
    readonly property bool complexInteraction: speed > 5
    readonly property var debugSignals: buildDebugSignals()

    // =========================================================================
    // 9. TABLEAU UNIVERSEL DES VOYANTS DU COMBINÉ
    // =========================================================================
    readonly property var indicators: [
        { code: "G", label: "Clignotant gauche", active: turnLeftActive, color: "#4DDB8A", blink: true },
        { code: "D", label: "Clignotant droit", active: turnRightActive, color: "#4DDB8A", blink: true },
        { code: "FEU", label: "Feux", active: lightsActive || highBeamActive || fogFrontActive || fogRearActive, color: "#4DDB8A", blink: false },
        { code: "STOP", label: "Frein", active: handbrakeActive || brakeWarning, color: "#FF4D5A", blink: false },
        { code: "CEINT", label: "Ceinture", active: driverUnbelted, color: "#FF4D5A", blink: false },
        { code: "PORTE", label: "Porte", active: doorOpen, color: "#FFB33B", blink: false },
        { code: "HUILE", label: "Huile", active: oilWarning, color: "#FF4D5A", blink: false },
        { code: "BAT", label: "Batterie", active: batteryWarning, color: "#FF4D5A", blink: false },
        { code: "ABS", label: "ABS", active: absWarning, color: "#FFB33B", blink: false },
        { code: "ESP", label: "ESP", active: espWarning, color: "#FFB33B", blink: false },
        { code: "MOT", label: "Moteur", active: engineWarning, color: "#FFB33B", blink: false }
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

    function presentedDomain(domainName) {
        const actual = vehicleState[domainName] || {}
        if (!presentationState.startup_active)
            return actual
        const overrideDomains = presentationState.domains || {}
        const override = overrideDomains[domainName] || {}
        const merged = {}
        Object.keys(actual).forEach(function(key) { merged[key] = actual[key] })
        Object.keys(override).forEach(function(key) { merged[key] = override[key] })
        return merged
    }

    function presentedStandaloneDomain(domainName, actual) {
        if (!presentationState.startup_active)
            return actual
        const overrideDomains = presentationState.domains || {}
        const override = overrideDomains[domainName] || {}
        const merged = {}
        Object.keys(actual).forEach(function(key) { merged[key] = actual[key] })
        Object.keys(override).forEach(function(key) { merged[key] = override[key] })
        return merged
    }

    function signalFresh(domainName, signalName) {
        if (presentationState.startup_active)
            return true
        const domainQuality = dataQuality[domainName] || {}
        const signal = domainQuality[signalName]
        return signal === undefined || signal.quality !== "STALE"
    }

    function serviceKeys(status) {
        const keys = Object.keys(serviceHealth)
        return keys.filter(function(key) {
            return serviceHealth[key] && serviceHealth[key].status === status
        })
    }

    function buildDebugSignals() {
        const rows = []
        const domainNames = ["powertrain", "motion", "wheels", "body", "assistance", "dynamics", "environment", "controls", "alerts"]
        domainNames.forEach(function(domainName) {
            const values = vehicleState[domainName] || {}
            const quality = dataQuality[domainName] || {}
            Object.keys(values).sort().forEach(function(key) {
                const metadata = quality[key] || {}
                rows.push({
                    domain: domainName,
                    key: key,
                    value: values[key],
                    unit: metadata.unit || "",
                    source: metadata.source || "",
                    quality: metadata.quality || "UNKNOWN",
                    ageMs: number(metadata.age_ms, 0)
                })
            })
        })
        return rows
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
