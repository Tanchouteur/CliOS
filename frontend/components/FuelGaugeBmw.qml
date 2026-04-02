import QtQuick

Item {
    id: root
    width: 250
    height: 250

    // ==========================================
    // VARIABLES DE DONNÉES
    // ==========================================
    property real fuel: bridge.data.fuel_level !== undefined ? bridge.data.fuel_level : 100

    // Pourcent de progression (0.0 à 1.0)
    property real percent: Math.min(Math.max(fuel / 100.0, 0.0), 1.0)

    property real smoothPercent: percent
    Behavior on smoothPercent { SpringAnimation { spring: 3.0; damping: 0.8 } }

    // ==========================================
    // 🛠️ GÉOMÉTRIE (Points à ajuster via Debug)
    // ==========================================
    // Note : Les points sont définis AVANT le miroir pour plus de simplicité
    property real p0X: width * 0.35;  property real p0Y: height * 0.91
    property real p0_cOutX: width * 0.60; property real p0_cOutY: height * 0.94
    property real p1X:  width * 0.75; property real p1Y: height * 0.62
    property real p1_cInX: width * 0.70; property real p1_cInY: height * 0.70
    property real p1_cOutX: width * 0.80; property real p1_cOutY: height * 0.50
    property real p2X:  width * 0.80; property real p2Y: height * 0.10
    property real p2_cInX: width * 1.0; property real p2_cInY: height * 0.30

    // Point de fuite vers le centre (droite car le container est miroir)
    property real vanishingPointX: width * -1.5
    property real vanishingPointY: height * -0
    Image {
        id: bgImage
        source: "../assets/bmw/FondFuel.png"
        fillMode: Image.PreserveAspectFit
        anchors.fill: parent
        z: 0
    }
    // -----------------------------------------------------------------
    // 🪞 LE MIROIR (Pour passer à gauche du tachymètre)
    // -----------------------------------------------------------------
    Item {
        id: mirrorContainer
        anchors.fill: parent
        transform: Scale { xScale: -1; origin.x: width / 2 }



        // CANVAS DEBUG (Jaune/Rouge)
        Canvas {
            anchors.fill: parent
            z: 999
            visible: false
            onPaint: {
                var ctx = getContext("2d");
                ctx.clearRect(0, 0, width, height);
                ctx.strokeStyle = "yellow"; ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(root.p0X, root.p0Y);
                ctx.bezierCurveTo(root.p0_cOutX, root.p0_cOutY, root.p1_cInX, root.p1_cInY, root.p1X, root.p1Y);
                ctx.bezierCurveTo(root.p1_cOutX, root.p1_cOutY, root.p2_cInX, root.p2_cInY, root.p2X, root.p2Y);
                ctx.stroke();
            }
        }

        Path {
            id: mainPath
            startX: root.p0X; startY: root.p0Y
            PathCubic { x: root.p1X; y: root.p1Y; control1X: root.p0_cOutX; control1Y: root.p0_cOutY; control2X: root.p1_cInX; control2Y: root.p1_cInY }
            PathCubic { x: root.p2X; y: root.p2Y; control1X: root.p1_cOutX; control1Y: root.p1_cOutY; control2X: root.p2_cInX; control2Y: root.p2_cInY }
        }

        Repeater {
            model: 200
            Item {
                id: fillDelegate
                property real myProgress: index / 200.0
                visible: myProgress <= root.smoothPercent
                PathInterpolator { id: segmentRail; progress: fillDelegate.myProgress; path: mainPath }

                Rectangle {
                    gradient: Gradient {
                        orientation: Gradient.Horizontal// 1. Le bord tranchant (Blanc pur)
                        GradientStop { position: 0.0; color: "#FFFFFF" }

                        // 2. La transition rapide (Gris clair)
                        // En mettant 0.05, on force le blanc à ne rester que sur le tout début
                        GradientStop { position: 0.1; color: "#FFFFFF" }
                        GradientStop { position: 0.11; color: "#4FFFFFFF" }

                        // 3. La profondeur (Gris sombre vers transparent)
                        GradientStop { position: 1.0; color: "#05808080" }
                    }
                    width: 45; height: 2
                    x: segmentRail.x; y: segmentRail.y - (height / 2)
                    transformOrigin: Item.Left
                    property real deltaY: root.vanishingPointY - segmentRail.y
                    property real deltaX: root.vanishingPointX - segmentRail.x
                    rotation: (Math.atan2(deltaY, deltaX) * 180 / Math.PI)
                }
            }
        }

        // ==========================================
        // LE TRAIT D'AIGUILLE ORANGE (Z=10)
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

            // Couleur Orange BMW typique
            color: "#ff6600"

            // Lueur externe (Glow) pour l'effet aiguille lumineuse
            layer.enabled: true
            layer.effect: ShaderEffect {
                //fragmentShader: "qrc:/qt-project.org/imports/QtQuick/Effects/shaders/fastglow.frag"
                // Si tu n'as pas les shaders, un simple Rectangle suffit
            }

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
                GradientStop { position: 1.0; color: "#aa4400" }
            }
        }
    }

    // ==========================================
    // TEXTE NUMÉRIQUE (À l'endroit, hors miroir)
    // ==========================================
    Text {
        z: 100
        text: root.fuel.toFixed(0)
        color: "white"
        font.pixelSize: 24; font.bold: true
        anchors.bottom: parent.bottom; anchors.left: parent.left
        anchors.bottomMargin: 15; anchors.leftMargin: 20
        // Miroir inversé pour le texte pour qu'il soit lisible
    }
}