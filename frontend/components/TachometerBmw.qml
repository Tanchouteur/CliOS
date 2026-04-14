import QtQuick
import "../style"

Item {
    id: root
    width: 500
    height: 400

    // --- Propriétés Publiques (Données Véhicule) ---
    property real rpm: bridge.data.rpm !== undefined ? bridge.data.rpm : 0
    property int max_rpm: bridge.config.tachometer.max_rpm !== undefined ? bridge.config.tachometer.max_rpm : 7000

    property int idle_rpm: bridge.config.tachometer.idle_rpm !== undefined ? bridge.config.tachometer.idle_rpm : 800
    property int redline_rpm: bridge.config.tachometer.redline_rpm !== undefined ? bridge.config.tachometer.redline_rpm : 6000

    property string currentGear: bridge.data.gear !== undefined ? bridge.data.gear : "Error"

    // --- Variables d'Animation ---
    property real smoothRpm: root.rpm

    // --- Géométrie et Perspective 3D ---
    property real vanishingPointX: width * 0.25
    property real vanishingPointY: height * 0.50

    // Points de contrôle de la courbe de Bézier (Rail du cadran)
    property real p0X: 270; property real p0Y: 390
    property real pC1X: 290; property real pC1Y: 390
    property real pC2X: 300; property real pC2Y: 390
    property real p1X: 320; property real p1Y: 385
    property real pC3X: 380; property real pC3Y: 350
    property real pC4X: 435; property real pC4Y: 240
    property real p2X: 441; property real p2Y: 200
    property real pC5X: 440; property real pC5Y: 150
    property real pC6X: 340; property real pC6Y: 70
    property real p3X: 290; property real p3Y: 50
    property real pC7X: 280; property real pC7Y: 40
    property real pC8X: 150; property real pC8Y: 17
    property real p4X: 65; property real p4Y: 17

    property real needleAngleOffset: 90

    // Coefficients de progression sur le chemin
    property real coefP1: 0.05
    property real coefP2: 0.40
    property real coefP3: 0.70

    // --- Fond du Compteur ---
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
        progress: Math.min(Math.max(root.smoothRpm / root.max_rpm, 0.0), 1.0)
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

                // Décalage du segment le long de l'axe de perspective
                x: trailRail.x + offsetInward * Math.cos(parent.angleToVPRad) - width
                y: trailRail.y + offsetInward * Math.sin(parent.angleToVPRad) - (height / 2)

                transformOrigin: Item.Right
                rotation: parent.angleFromVPRad * 180 / Math.PI
            }
        }
    }

    // --- Aiguille Principale ---
    Item {
        z: 10
        width: 65; height: 12

        // Calcul de l'alignement sur le point de fuite
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
                ctx.shadowColor = Theme.main; ctx.shadowBlur = 8;
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
        model: Math.round(root.max_rpm / 100) + 1

        Item {
            id: tickDelegate
            property int tickRpm: index * 100

            // Classification des graduations (Majeure, Mineure)
            property bool is1000: tickRpm % 1000 === 0
            property bool is500: tickRpm % 500 === 0 && !is1000

            // Coloration contextuelle (Ralenti et Zone Rouge)
            property color tickColor: (tickRpm === root.idle_rpm || tickRpm >= root.redline_rpm) ? Theme.redLine : "white"

            // Effet de mise en valeur au passage de l'aiguille
            property real distanceToNeedle: Math.abs(tickDelegate.tickRpm - root.smoothRpm)
            property real proximity: Math.max(0.0, 1.0 - (distanceToNeedle / 800.0))

            PathInterpolator {
                id: tickRail
                progress: tickDelegate.tickRpm / root.max_rpm
                path: mainPath
            }

            // Calcul de l'angle d'alignement pour chaque graduation
            property real deltaY: root.vanishingPointY - tickRail.y
            property real deltaX: root.vanishingPointX - tickRail.x
            property real angleToCenterRad: Math.atan2(deltaY, deltaX)
            property real angleToCenterDeg: angleToCenterRad * 180 / Math.PI

            // Trait de graduation
            Rectangle {
                z: 20
                width: tickDelegate.is1000 ? 28 : (tickDelegate.is500 ? 18 : 8)
                height: tickDelegate.is1000 ? 3 : 2

                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: tickDelegate.tickColor }
                    GradientStop { position: 1.0; color: "transparent" }
                }

                x: tickRail.x
                y: tickRail.y - (height / 2)
                transformOrigin: Item.Left
                rotation: tickDelegate.angleToCenterDeg
            }

            // Étiquette numérique (Milliers de tours/min)
            Text {
                z: 30
                visible: tickDelegate.is1000
                text: tickDelegate.tickRpm / 1000
                color: tickDelegate.tickColor
                font.pixelSize: 32
                font.bold: true
                font.family: "Arial"

                opacity: 0.70 + (tickDelegate.proximity * 0.7)
                scale: 1.0 + (tickDelegate.proximity * 0.5)


                property real textOffset: 45

                // Positionnement le long du rayon calculé (Perspective)
                x: tickRail.x + textOffset * Math.cos(tickDelegate.angleToCenterRad) - (width / 2)
                y: tickRail.y + textOffset * Math.sin(tickDelegate.angleToCenterRad) - (height / 2)
            }
        }
    }

    // --- Affichage du Rapport Engagé ---
    Text {
        z: 100
        text: root.currentGear
        color: "white"
        font.pixelSize: 80
        font.bold: true
        font.family: "Arial"

        anchors.centerIn: parent
        anchors.horizontalCenterOffset: -40
        anchors.verticalCenterOffset: 10
    }

    EngineTempGaugeBmw {
        anchors.fill: parent

        p0X: root.p0X
        p0Y: root.p0Y
        vanishingPointX: root.vanishingPointX
        vanishingPointY: root.vanishingPointY
    }

}