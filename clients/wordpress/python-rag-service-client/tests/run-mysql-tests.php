<?php
/**
 * MySQL coverage for the production reservation class.
 *
 * Requires RAG_TEST_MYSQL_HOST, RAG_TEST_MYSQL_USER, and RAG_TEST_MYSQL_DATABASE.
 * RAG_TEST_MYSQL_PASSWORD and RAG_TEST_MYSQL_PORT are optional. The runner sets
 * a unique RAG_TEST_MYSQL_PREFIX and drops that table when it finishes.
 */

require_once __DIR__ . '/mysql-wpdb.php';
require_once __DIR__ . '/stale-scenario.php';

$rag_test_checks   = 0;
$rag_test_failures = array();

function rag_check( bool $condition, string $message ): void {
	global $rag_test_checks, $rag_test_failures;

	++$rag_test_checks;
	if ( ! $condition ) {
		$rag_test_failures[] = $message;
		fwrite( STDERR, "FAIL {$message}\n" );
	}
}

function rag_group( string $name ): void {
	echo "\n[{$name}]\n";
}

/**
 * @param string[] $command Worker command.
 * @return array<int, string>
 */
function rag_mysql_workers( array $command, int $count ): array {
	$processes = array();
	for ( $i = 0; $i < $count; $i++ ) {
		$pipes = array();
		$process = proc_open(
			$command,
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		$processes[] = array( $process, $pipes );
	}
	$outcomes = array();
	foreach ( $processes as $entry ) {
		$stdout = trim( (string) stream_get_contents( $entry[1][1] ) );
		$stderr = trim( (string) stream_get_contents( $entry[1][2] ) );
		fclose( $entry[1][1] );
		fclose( $entry[1][2] );
		proc_close( $entry[0] );
		$outcomes[] = $stdout;
		if ( '' !== $stderr ) {
			fwrite( STDERR, $stderr . "\n" );
		}
	}
	return $outcomes;
}

putenv( 'RAG_TEST_MYSQL_PREFIX=rt' . bin2hex( random_bytes( 4 ) ) . '_' );
echo 'MySQL production reservation tests. Prefix ' . getenv( 'RAG_TEST_MYSQL_PREFIX' ) . "\n";

rag_group( '[mysql-concurrent-admission] forty connections share one counter' );
$database = rag_mysql_production_database();
$outcomes = rag_mysql_workers(
	array( PHP_BINARY, __DIR__ . '/concurrency-worker.php', 'mysql', 'search', '10', '1700000060' ),
	40
);
$counts = array_count_values( $outcomes );
rag_check( 10 === ( $counts['admitted'] ?? 0 ), 'mysql concurrent admitted ' . ( $counts['admitted'] ?? 0 ) . ' of 10' );
rag_check( 30 === ( $counts['exhausted'] ?? 0 ), 'mysql concurrent exhausted ' . ( $counts['exhausted'] ?? 0 ) . ' of 30' );
rag_check( 0 === ( $counts['failed'] ?? 0 ), 'mysql concurrent storage failures ' . ( $counts['failed'] ?? 0 ) );
$rows = $GLOBALS['wpdb']->rate_rows();
rag_check( 1 === count( $rows ) && 10 === (int) $rows[0]['request_count'], 'mysql stored count stopped at the limit' );

rag_group( '[mysql-rollover] a new minute resets, then the next reservation increments' );
$limiter = new RAG_Service_Rate_Limiter( $database );
$first   = $limiter->reserve( 'search', 10, 1700000100 );
$second  = $limiter->reserve( 'search', 10, 1700000105 );
rag_check( is_array( $first ) && true === $first['allowed'], 'first request in the new minute is admitted' );
rag_check( is_array( $second ) && true === $second['allowed'], 'second request in the new minute is admitted' );
$rolled = $GLOBALS['wpdb']->rate_rows();
$search = null;
foreach ( $rolled as $row ) {
	if ( 'search' === $row['route'] ) {
		$search = $row;
	}
}
rag_check( is_array( $search ) && '1700000100' === (string) $search['window_start'] && 2 === (int) $search['request_count'], 'two new-minute requests stored 2' );

rag_group( '[mysql-concurrent-rollover] one new minute admits the limit once' );
$database = rag_mysql_production_database();
$limiter  = new RAG_Service_Rate_Limiter( $database );
for ( $i = 0; $i < 5; $i++ ) {
	$filled = $limiter->reserve( 'search', 5, 1700000060 );
	rag_check( is_array( $filled ) && true === $filled['allowed'], "old minute admission {$i}" );
}
$rollover_outcomes = rag_mysql_workers(
	array( PHP_BINARY, __DIR__ . '/concurrency-worker.php', 'mysql', 'search', '5', '1700000100' ),
	20
);
$rollover_counts = array_count_values( $rollover_outcomes );
rag_check( 5 === ( $rollover_counts['admitted'] ?? 0 ), 'mysql rollover admitted ' . ( $rollover_counts['admitted'] ?? 0 ) . ' of 5' );
rag_check( 15 === ( $rollover_counts['exhausted'] ?? 0 ), 'mysql rollover exhausted ' . ( $rollover_counts['exhausted'] ?? 0 ) . ' of 15' );
$rollover_rows = $GLOBALS['wpdb']->rate_rows();
rag_check( 1 === count( $rollover_rows ) && '1700000100' === (string) $rollover_rows[0]['window_start'] && 5 === (int) $rollover_rows[0]['request_count'], 'mysql rollover stored the new minute at the limit' );

rag_group( '[mysql-stale-same-route] delayed search is rejected after search cleanup' );
$database = rag_mysql_production_database();
$limiter  = new RAG_Service_Rate_Limiter( $database );
$ready    = tempnam( sys_get_temp_dir(), 'rag-ready-' );
$release  = $ready . '-release';
unlink( $ready );
$errors = rag_test_stale_window(
	$limiter,
	function () use ( $ready, $release ) {
		$pipes = array();
		$process = proc_open(
			array( PHP_BINARY, __DIR__ . '/stale-worker.php', 'mysql', 'search', '2', '1700000060', $ready, $release ),
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		return array( $process, $pipes, $ready, $release );
	},
	function () {
		return $GLOBALS['wpdb']->rate_rows();
	},
	'search',
	1700000060,
	1700000100,
	2
);
foreach ( $errors as $error ) {
	rag_check( false, $error );
}
rag_check( array() === $errors, 'mysql same-route stale worker stayed exhausted' );
@unlink( $ready );
@unlink( $release );

rag_group( '[mysql-stale-other-route] delayed search is rejected after ask cleanup' );
$database = rag_mysql_production_database();
$limiter  = new RAG_Service_Rate_Limiter( $database );
$ready    = tempnam( sys_get_temp_dir(), 'rag-ready-' );
$release  = $ready . '-release';
unlink( $ready );
$errors = rag_test_stale_window(
	$limiter,
	function () use ( $ready, $release ) {
		$pipes = array();
		$process = proc_open(
			array( PHP_BINARY, __DIR__ . '/stale-worker.php', 'mysql', 'search', '2', '1700000060', $ready, $release ),
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		return array( $process, $pipes, $ready, $release );
	},
	function () {
		return $GLOBALS['wpdb']->rate_rows();
	},
	'answer',
	1700000060,
	1700000100,
	2
);
foreach ( $errors as $error ) {
	rag_check( false, $error );
}
rag_check( array() === $errors, 'mysql other-route stale worker stayed exhausted' );
@unlink( $ready );
@unlink( $release );

rag_group( '[mysql-storage-failure] a missing table does not admit' );
$database = rag_mysql_production_database();
$limiter  = new RAG_Service_Rate_Limiter( $database );
$table    = $GLOBALS['wpdb']->prefix . 'rag_service_rate_limits';
$GLOBALS['wpdb']->query( "DROP TABLE {$table}" );
rag_check( null === $limiter->reserve( 'search', 10, 1700000060 ), 'mysql storage failure returns null' );

rag_group( '[mysql-client-found-rows] an unchanged row is rejected when the flag reports one affected row' );
$database = rag_mysql_production_database( MYSQLI_CLIENT_FOUND_ROWS );
$limiter  = new RAG_Service_Rate_Limiter( $database );
$created  = $limiter->reserve( 'search', 1, 1700000060 );
rag_check( is_array( $created ) && true === $created['allowed'], 'insert under CLIENT_FOUND_ROWS is admitted' );
rag_check( 1 === $GLOBALS['wpdb']->last_upsert_affected, 'insert affected rows is 1' );
$changed = $limiter->reserve( 'search', 2, 1700000061 );
rag_check( is_array( $changed ) && true === $changed['allowed'], 'a real increment under CLIENT_FOUND_ROWS is admitted' );
rag_check( 2 === $GLOBALS['wpdb']->last_upsert_affected, 'a changed row reports 2 affected rows' );
$noop = $limiter->reserve( 'search', 2, 1700000062 );
rag_check( is_array( $noop ) && false === $noop['allowed'], 'CLIENT_FOUND_ROWS no-op is rejected' );
rag_check( 1 === $GLOBALS['wpdb']->last_upsert_affected, 'CLIENT_FOUND_ROWS reports the no-op as 1 affected row' );
$rows = $GLOBALS['wpdb']->rate_rows();
rag_check( 1 === count( $rows ) && 2 === (int) $rows[0]['request_count'], 'the rejected no-op did not increment the count' );

$plain = rag_mysql_use( 0 );
$limiter = new RAG_Service_Rate_Limiter( $database );
$plain_noop = $limiter->reserve( 'search', 2, 1700000063 );
rag_check( is_array( $plain_noop ) && false === $plain_noop['allowed'], 'without CLIENT_FOUND_ROWS the full minute is also rejected' );
rag_check( 0 === $plain->last_upsert_affected, 'without the flag the no-op reports 0 affected rows' );

$table = $GLOBALS['wpdb']->prefix . 'rag_service_rate_limits';
$GLOBALS['wpdb']->query( "DROP TABLE IF EXISTS {$table}" );

echo $rag_test_checks . " checks, " . count( $rag_test_failures ) . " failed\n";
exit( array() === $rag_test_failures ? 0 : 1 );
