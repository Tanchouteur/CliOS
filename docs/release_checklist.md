# Checklist de publication CliOS 2.0.1

Cette checklist sépare la publication de la dernière préversion de la décision
de promouvoir CliOS 2.0.1 en version stable. Une RC publiée n'est jamais
transformée sur place : la stable est reconstruite depuis un nouveau commit où
`VERSION` vaut exactement `2.0.1`.

## Publication de v2.0.1-rc.10

- [ ] la PR de préparation de RC10 est fusionnée dans `main` avec tous les jobs CI verts ;
- [ ] `VERSION` vaut `2.0.1-rc.10` sur le commit de `main` à taguer ;
- [ ] le tag est exactement `v2.0.1-rc.10` et pointe sur ce commit de `main` ;
- [ ] la release GitHub est marquée comme préversion ;
- [ ] les archives Bookworm et Trixie ARM64, les deux manifestes `beta`, `SHA256SUMS` et `SHA256SUMS.sig` sont publiés ;
- [ ] le workflow de release valide les deux archives ARM64 et publie leurs attestations ;
- [ ] une machine sur le canal bêta détecte RC10 depuis une RC antérieure.

Le workflow déduit automatiquement le canal `beta` du suffixe `-rc.10`. Il
accepte les tags GitHub ordinaires ; la confiance de l'updater repose sur la
signature Ed25519 des artefacts de release.

## Qualification de RC10

- [ ] la fiche `docs/qualification_v2.0.1.md` est entièrement complétée ;
- [ ] aucune anomalie bloquante ne subsiste après plusieurs démarrages à froid et trajets ;
- [ ] l'installation propre et la mise à jour par le cockpit ont toutes deux été essayées ;
- [ ] l'activation saine et le rollback N-1 ont été observés sur Raspberry Pi ;
- [ ] les modes USB, stockage interne et OverlayFS/RAM ont été vérifiés ;
- [ ] l'extinction contact/CAN et son inhibition pendant une mise à jour ont été vérifiées ;
- [ ] les journaux et bundles diagnostics utiles sont conservés avec la fiche de test.

## Publication de v2.0.1 stable

- [ ] aucune fonctionnalité supplémentaire n'a été ajoutée après la qualification de RC10 ;
- [ ] les seuls changements post-RC sont le numéro de version, les notes de release ou une correction bloquante explicitement requalifiée ;
- [ ] `VERSION` vaut exactement `2.0.1` ;
- [ ] les notes de version et la fiche de qualification reflètent le résultat final ;
- [ ] tous les jobs CI du commit stable sont verts ;
- [ ] le tag `v2.0.1` pointe sur le commit validé de `main` ;
- [ ] la release GitHub n'est ni un brouillon ni une préversion ;
- [ ] les deux manifestes publiés portent le canal `stable` ;
- [ ] les hashes, la signature Ed25519 et les attestations sont présents ;
- [ ] une installation RC10 sur le canal bêta détecte et active `2.0.1` ;
- [ ] une installation 2.0.0 sur le canal stable détecte `2.0.1` ;
- [ ] un dernier démarrage et un contrôle des données sont effectués après mise à jour.

## Commandes utiles sur le Raspberry Pi

```bash
python3 /opt/clios/current/tools/release_cli.py channel
python3 /opt/clios/current/tools/release_cli.py channel beta
python3 /opt/clios/current/tools/release_cli.py check
python3 /opt/clios/current/tools/release_cli.py stage 2.0.1-rc.10
python3 /opt/clios/current/tools/release_cli.py rollback
```

La qualification Raspberry Pi 4 reste différée et ne bloque pas 2.0.1.
