-- Schéma (cahier technique §4) ajusté par les fiches ALG-04 (écarts 1 à 4, version 2 du 2026-11-13).
-- Modifications par rapport au cahier : clé de scrutin_group_votes = (scrutin_id, rang) avec
-- groupe_id nullable (groupes PO0) ; groupe_rang et cause sur les votes ; origine et groupe_rang
-- sur les mises au point ; etl_version sur scrutins.
CREATE TABLE IF NOT EXISTS scrutins (
  id TEXT PRIMARY KEY, numero INTEGER, legislature INTEGER, date_scrutin TEXT,
  titre TEXT, objet TEXT, type_vote_code TEXT, type_vote_libelle TEXT,
  resultat_code TEXT, source_url TEXT, source_hash TEXT, imported_at TEXT,
  etl_version TEXT
);
CREATE TABLE IF NOT EXISTS scrutin_totals (
  scrutin_id TEXT PRIMARY KEY REFERENCES scrutins(id),
  pour INTEGER, contre INTEGER, abstentions INTEGER, non_votants INTEGER,
  suffrages_exprimes INTEGER, nombre_votants INTEGER
);
CREATE TABLE IF NOT EXISTS groupes (id TEXT PRIMARY KEY, libelle TEXT, sigle TEXT);
CREATE TABLE IF NOT EXISTS scrutin_group_votes (
  scrutin_id TEXT REFERENCES scrutins(id), rang INTEGER,
  groupe_id TEXT REFERENCES groupes(id), membres INTEGER,
  pour INTEGER, contre INTEGER, abstentions INTEGER, non_votants INTEGER,
  position_majoritaire_source TEXT,
  PRIMARY KEY (scrutin_id, rang)
);
CREATE TABLE IF NOT EXISTS deputes (id TEXT PRIMARY KEY, nom TEXT, prenom TEXT);
CREATE TABLE IF NOT EXISTS scrutin_individual_votes (
  scrutin_id TEXT REFERENCES scrutins(id), depute_id TEXT REFERENCES deputes(id),
  groupe_rang INTEGER, groupe_id TEXT REFERENCES groupes(id),
  mandat_id TEXT, position TEXT, par_delegation INTEGER, cause TEXT,
  PRIMARY KEY (scrutin_id, depute_id)
);
CREATE TABLE IF NOT EXISTS scrutin_mises_au_point (
  scrutin_id TEXT REFERENCES scrutins(id), depute_id TEXT REFERENCES deputes(id),
  origine TEXT NOT NULL, groupe_rang INTEGER, groupe_id TEXT REFERENCES groupes(id),
  position_initiale TEXT, position_declaree TEXT NOT NULL, par_delegation INTEGER,
  PRIMARY KEY (scrutin_id, depute_id)
);
CREATE TABLE IF NOT EXISTS imports (
  id INTEGER PRIMARY KEY, started_at TEXT, finished_at TEXT, archive_sha256 TEXT,
  files_seen INTEGER, files_ok INTEGER, files_failed INTEGER, status TEXT, error_summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_scrutins_date ON scrutins(date_scrutin);
CREATE INDEX IF NOT EXISTS idx_scrutins_type ON scrutins(type_vote_code);
CREATE INDEX IF NOT EXISTS idx_sgv_groupe ON scrutin_group_votes(groupe_id);
CREATE INDEX IF NOT EXISTS idx_siv_depute ON scrutin_individual_votes(depute_id);
