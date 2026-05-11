# statspro-dashboard

Outil de pilotage PoC NBA : filtrage, suivi et export des 163 données candidates du dashboard StatsPro.
Conçu pour survivre à plusieurs cycles de PoC sans dériver du réel ni nécessiter une stack lourde.

Voir CLAUDE.md et IMPLEMENTATION.md à la racine pour les invariants et le plan d'exécution.

## Ouvrir en local

```bash
python -m http.server 8000
```

Puis ouvrir [http://localhost:8000/dashboard_statspro.html](http://localhost:8000/dashboard_statspro.html).
