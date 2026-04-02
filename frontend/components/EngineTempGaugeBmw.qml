import QtQuick

Item {
    id: root
    width: 250 // Dimensions de test pour l'intégration finale
    height: 250

    // ==========================================
    // VARIABLES DE DONNÉES (BLINDÉES)
    // ==========================================
    property real temperature: bridge.data.engine_temp !== undefined ? bridge.data.engine_temp : 50

    property int minTemperature: (bridge.config.temperature && bridge.config.temperature.min !== undefined) ? bridge.config.temperature.min : 30
    property int maxTemperature: (bridge.config.temperature && bridge.config.temperature.max !== undefined) ? bridge.config.temperature.max : 130

    property real percent: Math.min(Math.max((temperature - minTemperature) / (maxTemperature - minTemperature), 0.0), 1.0)

    property real smoothPercent: percent
    Behavior on smoothPercent { SpringAnimation { spring: 15.0; damping: 0.8 } }

    // ==========================================
    // 🛠️ LA GÉOMÉTRIE DE PRÉCISION (2 SEGMENTS CHAÎNÉS)
    // ==========================================
    property real p0X: width * 0.35;  property real p0Y: height * 0.91
    property real p0_cOutX: width * 0.60; property real p0_cOutY: height * 0.94
    property real p1X:  width * 0.75; property real p1Y: height * 0.62
    property real p1_cInX: width * 0.70; property real p1_cInY: height * 0.70
    property real p1_cOutX: width * 0.80; property real p1_cOutY: height * 0.50
    property real p2X:  width * 0.80; property real p2Y: height * 0.12
    property real p2_cInX: width * 1; property real p2_cInY: height * 0.30

    property real segmentAngleOffset: 90

    // ==========================================
    // 👁️ LE POINT DE FUITE (PERSPECTIVE 3D)
    // ==========================================
    property real vanishingPointX: width * -5.0
    property real vanishingPointY: height * -1

    // ==========================================
    // 0. FOND STATIQUE (Image)
    // ==========================================
    Image {
        id: bgImage
        source: "../assets/bmw/FondTemp.png"
        fillMode: Image.PreserveAspectFit
        anchors.fill: parent
        z: 0
    }

    // ==========================================
    // 🔍 L'OUTIL DE DEBUG VISUEL SÉQUENTIEL
    // ==========================================
    Canvas {
        id: debugCanvas
        anchors.fill: parent
        z: 999
        opacity: 0.8
        visible: false

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            ctx.beginPath();
            ctx.lineWidth = 2;
            ctx.strokeStyle = "yellow";
            ctx.moveTo(root.p0X, root.p0Y);
            ctx.bezierCurveTo(root.p0_cOutX, root.p0_cOutY, root.p1_cInX, root.p1_cInY, root.p1X, root.p1Y);
            ctx.bezierCurveTo(root.p1_cOutX, root.p1_cOutY, root.p2_cInX, root.p2_cInY, root.p2X, root.p2Y);
            ctx.stroke();

            function drawPoint(x, y, color, size) {
                ctx.fillStyle = color;
                ctx.fillRect(x - size/2, y - size/2, size, size);
            }

            drawPoint(root.p0X, root.p0Y, "red", 8);
            drawPoint(root.p1X, root.p1Y, "red", 8);
            drawPoint(root.p2X, root.p2Y, "red", 8);

            drawPoint(root.p0_cOutX, root.p0_cOutY, "#00aaff", 4);
            drawPoint(root.p1_cInX, root.p1_cInY, "#00aaff", 4);
            drawPoint(root.p1_cOutX, root.p1_cOutY, "#00aaff", 4);
            drawPoint(root.p2_cInX, root.p2_cInY, "#00aaff", 4);
        }
    }

    // ==========================================
    // 1. DÉFINITION DU PATH UNIQUE CHAÎNÉ
    // ==========================================
    Path {
        id: mainPath
        startX: root.p0X; startY: root.p0Y
        PathCubic {
            x: root.p1X; y: root.p1Y;
            control1X: root.p0_cOutX; control1Y: root.p0_cOutY;
            control2X: root.p1_cInX; control2Y: root.p1_cInY;
        }
        PathCubic {
            x: root.p2X; y: root.p2Y;
            control1X: root.p1_cOutX; control1Y: root.p1_cOutY;
            control2X: root.p2_cInX; control2Y: root.p2_cInY;
        }
    }

    // ==========================================
    // 2. LA BARRE DYNAMIQUE (PERSPECTIVE 3D - POINT DE FUITE)
    // ==========================================
    Repeater {
        model: 250

        Item {
            id: fillDelegate
            z: 5

            property real myProgress: index / 250.0
            visible: myProgress <= root.smoothPercent

            PathInterpolator {
                id: segmentRail
                progress: fillDelegate.myProgress
                path: mainPath
            }

            Rectangle {
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    // 1. Le bord tranchant (Blanc pur)
                    GradientStop { position: 0.0; color: "#FFFFFF" }

                    // 2. La transition rapide (Gris clair)
                    // En mettant 0.05, on force le blanc à ne rester que sur le tout début
                    GradientStop { position: 0.1; color: "#FFFFFF" }
                    GradientStop { position: 0.11; color: "#4FFFFFFF" }

                    // 3. La profondeur (Gris sombre vers transparent)
                    GradientStop { position: 1.0; color: "#05808080" }
                }

                width: 55
                height: 2

                // CORRECTION 1 : Le point de départ (X) est directement sur le rail
                x: segmentRail.x
                y: segmentRail.y - (height / 2)

                // CORRECTION 2 : On plante le pivot à GAUCHE de la barre (sur le rail)
                transformOrigin: Item.Left

                property real deltaY: root.vanishingPointY - segmentRail.y
                property real deltaX: root.vanishingPointX - segmentRail.x

                // Le point de fuite étant maintenant à gauche de l'écran (X négatif),
                // et notre pivot étant à gauche, la barre va pivoter *vers l'intérieur* de l'écran.
                rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)
            }
        }
    }

    // ==========================================
        // NOUVEAU : LE TRAIT D'AIGUILLE ORANGE (Z=10)
        // ==========================================
        PathInterpolator {
            id: headNeedleRail
            // On le place pile sur la valeur actuelle lissée
            progress: root.smoothPercent
            path: mainPath
        }

        Rectangle {
            z: 10 // Au-dessus des segments blancs (5)
            visible: root.smoothPercent > 0.02 // On le cache si la jauge est à zéro

            width: 48  // Un peu plus long que les segments (45) pour dépasser légèrement
            height: 6  // Plus épais que les segments (2) pour bien le voir
            radius: 0

            // Couleur Orange BMW typique
            color: "#ff6600"

            // Positionnement sur le rail
            x: headNeedleRail.x
            y: headNeedleRail.y - (height / 2)

            transformOrigin: Item.Left

            // Même calcul de perspective que les segments
            property real deltaY: root.vanishingPointY - headNeedleRail.y
            property real deltaX: root.vanishingPointX - headNeedleRail.x
            rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)

            // Petit effet de dégradé pour la profondeur orange
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#ff8800" }
                GradientStop { position: 1.0; color: "#7c3201" }
            }
        }

    // ==========================================
    // 3. LA TEMPÉRATURE NUMÉRIQUE (Z=100)
    // ==========================================
    Text {
        z: 100
        // On affiche la valeur arrondie, avec le petit symbole degré !
        text: root.temperature.toFixed(0) + ""

        color: "white"
        font.pixelSize: 24// À ajuster selon la place
        font.bold: true
        font.family: "Arial"

        // On l'aimante en bas à droite du cadre de la jauge
        anchors.bottom: parent.bottom
        anchors.right: parent.right

        // On le repousse un peu vers l'intérieur pour qu'il ne touche pas les bords
        anchors.bottomMargin: 15
        anchors.rightMargin: 29

        // Petit effet pour que ça s'intègre bien au fond noir
        opacity: 0.9
    }
}