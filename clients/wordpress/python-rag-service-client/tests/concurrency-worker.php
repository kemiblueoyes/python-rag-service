<?php
/**
 * One admission against the shared SQLite database.
 *
 * Usage: php concurrency-worker.php <database> <route> <limit> <unix-time>
 */

require_once __DIR__ . '/sqlite-rate-limit-database.php';

$database = new Rag_Sqlite_Rate_Limit_Database( $argv[1] );
$limiter  = new RAG_Service_Rate_Limiter( $database );
$result   = $limiter->reserve( $argv[2], (int) $argv[3], (int) $argv[4] );

if ( null === $result ) {
	echo "failed\n";
	exit( 0 );
}

echo $result['allowed'] ? "admitted\n" : "exhausted\n";
