<?php
/**
 * Pause before reservation, then reserve one stale minute.
 *
 * sqlite: php stale-worker.php sqlite <database> <route> <limit> <unix-time> <ready-file> <release-file>
 * mysql:  php stale-worker.php mysql <route> <limit> <unix-time> <ready-file> <release-file>
 */

$driver = $argv[1] ?? '';

if ( 'sqlite' === $driver ) {
	require_once __DIR__ . '/sqlite-rate-limit-database.php';
	$database = new Rag_Sqlite_Rate_Limit_Database( $argv[2] );
	$route    = $argv[3];
	$limit    = (int) $argv[4];
	$now      = (int) $argv[5];
	$ready    = $argv[6];
	$release  = $argv[7];
} elseif ( 'mysql' === $driver ) {
	require_once __DIR__ . '/mysql-wpdb.php';
	$database = new RAG_Service_Wpdb_Rate_Limit_Database();
	rag_mysql_use( 0 );
	$route    = $argv[2];
	$limit    = (int) $argv[3];
	$now      = (int) $argv[4];
	$ready    = $argv[5];
	$release  = $argv[6];
} else {
	fwrite( STDERR, "Unknown driver {$driver}\n" );
	exit( 2 );
}

file_put_contents( $ready, 'ready' );
$deadline = microtime( true ) + 10;
while ( ! is_file( $release ) ) {
	if ( microtime( true ) > $deadline ) {
		echo "failed\n";
		exit( 0 );
	}
	usleep( 20000 );
}

$limiter = new RAG_Service_Rate_Limiter( $database );
$result  = $limiter->reserve( $route, $limit, $now );
if ( null === $result ) {
	echo "failed\n";
	exit( 0 );
}

echo $result['allowed'] ? "admitted\n" : "exhausted\n";
