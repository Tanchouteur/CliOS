pragma Singleton
import QtQuick

QtObject {
    // Tes couleurs générales
    readonly property color bgNoir: "#232120"
    readonly property color texteBlanc: "#f3f3f3"

    // Tes couleurs de jauges dynamiques
    readonly property color jaugeNormale: "#00aaff" // Bleu
    readonly property color jaugeAlerte: "#ff0033"  // Rouge

    // Ta banque de voyants
    readonly property color voyantVert: "#2ecc71"
    readonly property color voyantRouge: "#e74c3c"
    readonly property color voyantBleu: "#3498db"   // Phares
    readonly property color voyantOrange: "#e67e22" // Moteur
}