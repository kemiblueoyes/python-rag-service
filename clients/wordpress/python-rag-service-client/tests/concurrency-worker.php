<?php
/**
 * One admission against shared storage.
 *
 * sqlite: php concurrency-worker.php <database> <route> <limit> <unix-time>
 * mysql:  php concurrency-worker.php mysql <route> <limit> <unix-time>
 */

if ( 'mysql' === ( $argv[1] ?? '' ) ) {
	require_once __DIR__ . '/mysql-wpdb.php';
	rag_mysql_use( 0 );
	$database = new RAG_Service_Wpdb_Rate_Limit_Database();
	$route    = $argv[2];
	$limit    = (int) $argv[3];
	$now      = (int) $argv[4];
} else {
	require_once __DIR__ . '/sqlite-rate-limit-database.php';
	$database = new Rag_Sqlite_Rate_Limit_Database( $argv[1] );
	$route    = $argv[2];
	$limit    = (int) $argv[3];
	$now      = (int) $argv[4];
}

$limiter = new RAG_Service_Rate_Limiter( $database );
$result  = $limiter->reserve( $route, $limit, $now );

if ( null === $result ) {
	echo "failed\n";
	exit( 0 );
}

echo $result['allowed'] ? "admitted\n" : "exhausted\n";
