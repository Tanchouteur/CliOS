import QtQuick
import "../style"

Item {
    id: root
    width: 500
    height: 400

    // --- Propriétés Publiques (Données Véhicule) ---
    property real speed: bridge.data.speed !== undefined ? bridge.data.speed : 0
    property int max_speed: bridge.config.speedometer.max_speed !== undefined ? bridge.config.speedometer.max_speed : 260

    property real targetSpeed: bridge.data.vitesse_regulateur !== undefined ? bridge.data.vitesse_regulateur : 0
    property int regMode: bridge.data.regulateur_mode !== undefined ? bridge.data.regulateur_mode : 0
    property int regStatut: bridge.data.regulateur_statut !== undefined ? bridge.data.regulateur_statut : 0

    property real inst_cons: bridge.stats.inst_cons !== undefined ? bridge.stats.inst_cons : 0.0
    property real max_inst_cons: bridge.config.instant_fuel_consumption.max_display !== undefined ? bridge.config.instant_fuel_consumption.max_display : 20.0

    // --- Variables d'Animation ---
    property real smoothSpeed: root.speed
    Behavior on smoothSpeed { SpringAnimation { spring: 10.0; damping: 0.9 } }

    property real smoothTargetSpeed: root.targetSpeed
    Behavior on smoothTargetSpeed { SpringAnimation { spring: 7.0; damping: 0.9 } }

    property real smoothInstCons: root.inst_cons
    Behavior on smoothInstCons { SpringAnimation { spring: 10.0; damping: 0.8 } }

    // --- Géométrie et Perspective 3D ---
    property real vanishingPointX: width * 0.25
    property real vanishingPointY: height * 0.50

    // Points de contrôle de la courbe de Bézier (Rail du cadran)
    property real p0X: 270;  property real p0Y: 390
    property real pC1X: 290; property real pC1Y: 390
    property real pC2X: 300; property real pC2Y: 390
    property real p1X:  320; property real p1Y: 385
    property real pC3X: 380; property real pC3Y: 350
    property real pC4X: 435; property real pC4Y: 240
    property real p2X:  441; property real p2Y: 200
    property real pC5X: 440; property real pC5Y: 150
    property real pC6X: 340; property real pC6Y: 70
    property real p3X:  290; property real p3Y: 50
    property real pC7X: 280; property real pC7Y: 40
    property real pC8X: 150; property real pC8Y: 17
    property real p4X:  65;  property real p4Y: 17

    property real needleAngleOffset: 90

    // Coefficients de progression sur le chemin
    property real coefP1: 0.05
    property real coefP2: 0.35
    property real coefP3: 0.70

    // --- Conteneur Inversé (Monde Miroir) ---
    // Les graphismes sont inversés horizontalement pour la symétrie du tableau de bord
    Item {
        id: mirrorContainer
        anchors.fill: parent
        transform: Scale { xScale: -1; origin.x: width / 2 }

        Image {
            id: bg
            anchors.fill: parent
            source: "../assets/bmw/FondCompteurBMW.png"
            fillMode: Image.PreserveAspectFit
            z: 0
        }

        // --- Définition du Chemin Principal ---
        Path {
            id: mainPath
            startX: root.p0X; startY: root.p0Y
            PathCubic { x: root.p1X; y: root.p1Y; control1X: root.pC1X; control1Y: root.pC1Y; control2X: root.pC2X; control2Y: root.pC2Y }
            PathPercent { value: root.coefP1 }
            PathCubic { x: root.p2X; y: root.p2Y; control1X: root.pC3X; control1Y: root.pC3Y; control2X: root.pC4X; control2Y: root.pC4Y }
            PathPercent { value: root.coefP2 }
            PathCubic { x: root.p3X; y: root.p3Y; control1X: root.pC5X; control1Y: root.pC5Y; control2X: root.pC6X; control2Y: root.pC6Y }
            PathPercent { value: root.coefP3 }
            PathCubic { x: root.p4X; y: root.p4Y; control1X: root.pC7X; control1Y: root.pC7Y; control2X: root.pC8X; control2Y: root.pC8Y }
            PathPercent { value: 1.0 }
        }

        // Interpolateur central : Définit la position courante de l'aiguille sur le chemin
        PathInterpolator {
            id: mainNeedleRail
            progress: Math.min(Math.max(root.smoothSpeed / root.max_speed, 0.0), 1.0)
            path: mainPath
        }

        // --- Barre de Remplissage (Sillage de l'aiguille) ---
        Repeater {
            property int nbPoints: 300
            model: nbPoints
            Item {
                id: fillDelegate
                z: 5
                property real myProgress: index / 300
                visible: fillDelegate.myProgress <= mainNeedleRail.progress

                PathInterpolator { id: trailRail; progress: fillDelegate.myProgress; path: mainPath }

                // Calcul trigonométrique pour orienter le segment vers le point de fuite
                property real angleToVPRad: Math.atan2(root.vanishingPointY - trailRail.y, root.vanishingPointX - trailRail.x)
                property real angleFromVPRad: Math.atan2(trailRail.y - root.vanishingPointY, trailRail.x - root.vanishingPointX)

                Rectangle {
                    width: 5; height: 3
                    color: Theme.mainLight; opacity: 0.7
                    property real offsetInward: 12

                    x: trailRail.x + offsetInward * Math.cos(parent.angleToVPRad) - width
                    y: trailRail.y + offsetInward * Math.sin(parent.angleToVPRad) - (height / 2)

                    transformOrigin: Item.Right
                    rotation: parent.angleFromVPRad * 180 / Math.PI
                }
            }
        }

        // --- Marqueur du Régulateur de Vitesse ---
        PathInterpolator {
            id: regNeedleRail
            progress: Math.min(Math.max(root.smoothTargetSpeed / root.max_speed, 0.0), 1.0)
            path: mainPath
        }

        Item {
            z: 60
            visible: root.targetSpeed > 0
            width: 14; height: 8

            property real deltaY: regNeedleRail.y - root.vanishingPointY
            property real deltaX: regNeedleRail.x - root.vanishingPointX

            x: regNeedleRail.x - width
            y: regNeedleRail.y - (height / 2)
            transformOrigin: Item.Right

            rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)

            Rectangle {
                anchors.fill: parent
                radius: 2
                property int safeMode: Math.round(root.regMode)
                property int safeStatut: Math.round(root.regStatut)

                // Coloration selon l'état du régulateur
                color: {
                    if (safeMode === 2 && safeStatut === 4) return Theme.redLine; // Régulateur Actif
                    if (safeMode === 3 && safeStatut === 4) return "#ffa500"; // Limiteur Actif
                    return Theme.unselected; // En attente
                }
                border.color: "white"
                border.width: (safeMode > 0 && safeStatut === 4) ? 1 : 0
            }
        }

        // --- Aiguille Principale ---
        Item {
            z: 10
            width: 65; height: 12

            property real deltaY: mainNeedleRail.y - root.vanishingPointY
            property real deltaX: mainNeedleRail.x - root.vanishingPointX

            x: mainNeedleRail.x - width
            y: mainNeedleRail.y - (height / 2)
            transformOrigin: Item.Right

            rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)

            Canvas {
                width: 55; height: 18
                anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                onPaint: {
                    var ctx = getContext("2d"); ctx.clearRect(0, 0, width, height);
                    ctx.shadowColor = Theme.main ; ctx.shadowBlur = 8;
                    ctx.fillStyle = Theme.main;
                    ctx.beginPath();
                    ctx.moveTo(width, height / 2);
                    ctx.lineTo(0, height / 2 - 3);
                    ctx.lineTo(0, height / 2 + 3);
                    ctx.closePath(); ctx.fill();
                }
            }
        }

        // --- Générateur de Graduations Dynamiques ---
        Repeater {
            model: Math.round(root.max_speed / 10) + 1

            Item {
                id: tickDelegate
                z: 20

                property int tickSpeed: index * 10

                // Classification des graduations
                property bool isMajor: tickSpeed % 20 === 0
                property bool isMinor: tickSpeed % 10 === 0 && !isMajor

                // Effet de mise en valeur au passage de l'aiguille
                property real distanceToNeedle: Math.abs(tickDelegate.tickSpeed - root.smoothSpeed)
                property real proximity: Math.max(0.0, 1.0 - (distanceToNeedle / 30.0))

                PathInterpolator {
                    id: tickRail
                    progress: tickDelegate.tickSpeed / root.max_speed
                    path: mainPath
                }

                property real deltaY: root.vanishingPointY - tickRail.y
                property real deltaX: root.vanishingPointX - tickRail.x
                property real angleToCenterRad: Math.atan2(deltaY, deltaX)
                property real angleToCenterDeg: angleToCenterRad * 180 / Math.PI

                // Trait de graduation
                Rectangle {
                    width: tickDelegate.isMajor ? 28 : 18
                    height: tickDelegate.isMajor ? 3 : 2

                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: "white" }
                        GradientStop { position: 1.0; color: "transparent" }
                    }

                    x: tickRail.x
                    y: tickRail.y - (height / 2)
                    transformOrigin: Item.Left
                    rotation: tickDelegate.angleToCenterDeg
                }

                // Étiquette numérique
                Text {
                    visible: tickDelegate.isMajor
                    text: tickDelegate.tickSpeed

                    width: 0; height: 0
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter

                    color: "white"
                    font.pixelSize: 22
                    font.bold: true
                    font.family: "Arial"

                    opacity: 0.60 + (tickDelegate.proximity * 0.4)
                    scale: 1.0 + (tickDelegate.proximity * 0.3)

                    Behavior on scale { SpringAnimation { spring: 10.0; damping: 0.8 } }
                    Behavior on opacity { NumberAnimation { duration: 50 } }

                    property real textOffset: 45

                    x: tickRail.x + textOffset * Math.cos(tickDelegate.angleToCenterRad)
                    y: tickRail.y + textOffset * Math.sin(tickDelegate.angleToCenterRad)

                    // Inversion individuelle pour contrer le miroir du conteneur parent
                    transform: Scale { xScale: -1; origin.x: 0 }
                }
            }
        }
    }

    // --- Affichage Numérique Central (Vitesse) ---
    Text {
        z: 100
        text: root.speed.toFixed(0)

        width: 200
        horizontalAlignment: Text.AlignHCenter

        color: "white"
        font.pixelSize: 60
        font.bold: true
        font.family: "Arial"

        anchors.centerIn: parent
        anchors.horizontalCenterOffset: 70
        anchors.verticalCenterOffset: 10
    }

    // --- Jauge de Consommation Instantanée ---
    InstantConsGaugeBmw {
        referenceWidth: root.width

        p0X: root.p0X
        p0Y: root.p0Y
        vanishingPointX: root.vanishingPointX
        vanishingPointY: root.vanishingPointY

        smoothInstCons: root.smoothInstCons
        maxInstCons: root.max_inst_cons
    }
}