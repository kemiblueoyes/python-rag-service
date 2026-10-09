<?php
/**
 * Plugin tests.
 *
 * Run: php clients/wordpress/python-rag-service-client/tests/run-tests.php
 *
 * WordPress stub tests fake REST, HTTP, and wpdb. They don't execute MySQL.
 * SQLite tests call RAG_Service_Rate_Limiter against a real database file.
 * The concurrent test starts multiple PHP processes against that same file.
 */

require_once __DIR__ . '/wp-stubs.php';

define( 'RAG_SERVICE_API_BASE_URL', 'http://rag.test/' );
define( 'RAG_SERVICE_API_KEY', 'rag-test-key-do-not-leak' );

require_once dirname( __DIR__ ) . '/python-rag-service-client.php';
require_once __DIR__ . '/sqlite-rate-limit-database.php';

$rag_test_failures = array();
$rag_test_checks   = 0;

/**
 * Record one assertion.
 *
 * @param bool   $condition Result.
 * @param string $message   Failure text.
 */
function rag_check( bool $condition, string $message ): void {
	global $rag_test_checks, $rag_test_failures;
	$rag_test_checks++;
	if ( ! $condition ) {
		$rag_test_failures[] = $message;
		fwrite( STDERR, "FAIL {$message}\n" );
	}
}

/**
 * @param string $label Group label.
 */
function rag_group( string $label ): void {
	echo $label . "\n";
}

/**
 * @return array{0: RAG_Service_REST_Controller, 1: Rag_Sqlite_Rate_Limit_Database, 2: object, 3: string}
 */
function rag_temp_path( string $prefix ): string {
	$dir = __DIR__ . '/tmp';
	if ( ! is_dir( $dir ) ) {
		mkdir( $dir, 0700, true );
	}
	$path = tempnam( $dir, $prefix );
	if ( false === $path ) {
		throw new RuntimeException( 'Could not create a temporary database file.' );
	}
	return $path;
}

function rag_sqlite_controller( int $now ): array {
	$path     = rag_temp_path( 'rag-limit-' );
	$database = new Rag_Sqlite_Rate_Limit_Database( $path );
	$database->create_table();
	$clock = new class( $now ) {
		public int $now;

		public function __construct( int $now ) {
			$this->now = $now;
		}

		public function __invoke(): int {
			return $this->now;
		}
	};
	$controller = new RAG_Service_REST_Controller( new RAG_Service_Rate_Limiter( $database ), $clock );
	return array( $controller, $database, $clock, $path );
}

/**
 * @param Rag_Sqlite_Rate_Limit_Database $database Database to close.
 * @param string                          $path     SQLite path.
 */
function rag_remove_sqlite( Rag_Sqlite_Rate_Limit_Database $database, string $path ): void {
	$database->close();
	foreach ( array( $path, $path . '-wal', $path . '-shm' ) as $file ) {
		if ( is_file( $file ) ) {
			unlink( $file );
		}
	}
}

/**
 * @param int    $status HTTP status.
 * @param string $body   Response body.
 * @return array<string, mixed>
 */
function rag_http( int $status, string $body ): array {
	return array(
		'response' => array( 'code' => $status ),
		'body'     => $body,
	);
}

/**
 * @param mixed $result Controller result.
 * @return array<string, mixed>
 */
function rag_visitor_json( $result ): array {
	if ( $result instanceof WP_REST_Response ) {
		return array(
			'message' => null,
			'data'    => $result->data,
			'status'  => $result->status,
		);
	}
	$data = $result->get_error_data();
	return array(
		'code'    => $result->get_error_code(),
		'message' => $result->get_error_message(),
		'data'    => $data,
		'status'  => is_array( $data ) ? $data['status'] : null,
	);
}

/**
 * @param mixed  $result   Controller result.
 * @param int    $status   Expected status.
 * @param string $message  Expected visitor message.
 * @param string $code     Expected error code.
 */
function rag_expect_error( $result, int $status, string $message, string $code ): void {
	$json = rag_visitor_json( $result );
	rag_check( $json['status'] === $status, "status {$status}, got " . var_export( $json['status'], true ) );
	rag_check( $json['message'] === $message, "message [{$message}], got [{$json['message']}]" );
	rag_check( $json['code'] === $code, "code {$code}, got {$json['code']}" );
	rag_check( array( 'status' ) === array_keys( $json['data'] ), 'visitor error data is only the status' );
	rag_check( ! str_contains( (string) $json['message'], 'rag-test-key-do-not-leak' ), 'visitor message contains the API key' );
	rag_check( ! str_contains( (string) $json['message'], 'detail-token' ), 'visitor message contains an upstream detail' );
	rag_check( ! str_contains( (string) $json['message'], 'visible-query' ), 'visitor message echoes the query' );
}

function rag_expect_no_forward(): void {
	rag_check( array() === $GLOBALS['rag_test_remote_posts'], 'Python was called' );
}

/**
 * @return array<string, mixed>
 */
function rag_last_post(): array {
	$posts = $GLOBALS['rag_test_remote_posts'];
	rag_check( 1 === count( $posts ), 'expected one Python call, got ' . count( $posts ) );
	return $posts[0];
}

/**
 * Run a settings worker in a fresh PHP process.
 *
 * @param string $scenario Scenario name.
 * @return string
 */
function rag_settings_scenario( string $scenario ): string {
	$command = array( PHP_BINARY, __DIR__ . '/settings-worker.php', $scenario );
	$pipes   = array();
	$process = proc_open(
		$command,
		array(
			1 => array( 'pipe', 'w' ),
			2 => array( 'pipe', 'w' ),
		),
		$pipes
	);
	$stdout = stream_get_contents( $pipes[1] );
	$stderr = stream_get_contents( $pipes[2] );
	fclose( $pipes[1] );
	fclose( $pipes[2] );
	$code = proc_close( $process );
	rag_check( 0 === $code, "settings scenario {$scenario} exited {$code}: {$stderr}" );
	return trim( (string) $stdout );
}

echo "WordPress stub tests fake REST, HTTP, and wpdb. They don't run MySQL.\n";
echo "SQLite tests use a real database file and the plugin rate limiter.\n";
echo "The concurrent test starts multiple PHP processes against that file.\n";

rag_group( '[wordpress-stubs] routes stay public and sanitize the query' );
$controller = new RAG_Service_REST_Controller();
$controller->register_routes();
rag_check( 2 === count( $GLOBALS['rag_test_routes'] ), 'two routes are registered' );
foreach ( $GLOBALS['rag_test_routes'] as $route ) {
	rag_check( 'python-rag-service/v1' === $route[0], 'route namespace' );
	rag_check( '__return_true' === $route[2]['permission_callback'], $route[1] . ' requires a login' );
	rag_check( 'sanitize_text_field' === $route[2]['args']['query']['sanitize_callback'], $route[1] . ' sanitize callback' );
}
$hook_names = array();
foreach ( $GLOBALS['rag_test_hooks'] as $hook ) {
	$hook_names[] = $hook[0] . ' ' . $hook[1] . ' ' . $hook[2];
}
rag_check( in_array( 'action plugins_loaded rag_service_maybe_install_rate_limit_storage', $hook_names, true ), 'plugins_loaded installs storage' );
rag_check( in_array( 'filter rest_post_dispatch rag_service_send_retry_after', $hook_names, true ), 'Retry-After filter is registered' );
rag_check( 'rag_service_install_rate_limit_storage' === $GLOBALS['rag_test_activation'], 'activation hook installs storage' );
rag_check( isset( $GLOBALS['rag_test_shortcodes']['python_rag_service'] ), 'shortcode remains registered' );

rag_group( '[wordpress-stubs] schema and conditional MySQL upsert' );
$sql = rag_service_rate_limit_schema_sql( 'wp_rag_service_rate_limits', 'DEFAULT CHARSET=utf8mb4' );
rag_check( str_contains( $sql, 'route varchar(32) NOT NULL' ), 'schema has route' );
rag_check( str_contains( $sql, 'window_start bigint(20) unsigned NOT NULL' ), 'schema has window_start' );
rag_check( str_contains( $sql, 'request_count bigint(20) unsigned NOT NULL' ), 'schema has request_count' );
rag_check( str_contains( $sql, 'PRIMARY KEY  (route, window_start)' ), 'schema primary key' );

class Rag_Stub_Wpdb {
	public string $prefix = 'wp_';
	public array $queries = array();
	public array $prepares = array();
	public bool $fail_insert = false;
	public int $insert_affected = 1;
	public ?string $found_table = 'wp_rag_service_rate_limits';

	public function get_charset_collate(): string {
		return 'DEFAULT CHARSET=utf8mb4';
	}

	public function esc_like( string $text ): string {
		return addcslashes( $text, '_%\\' );
	}

	public function prepare( string $query, mixed ...$args ): string {
		$this->prepares[] = array( $query, $args );
		return $query;
	}

	public function query( string $sql ): int|false {
		$this->queries[] = $sql;
		if ( $this->fail_insert && str_contains( $sql, 'INSERT' ) ) {
			return false;
		}
		if ( str_contains( $sql, 'INSERT' ) ) {
			return $this->insert_affected;
		}
		return 1;
	}

	public function get_var( string $sql ): ?string {
		$this->queries[] = $sql;
		return $this->found_table;
	}
}

global $wpdb;
$wpdb = new Rag_Stub_Wpdb();
rag_service_maybe_install_rate_limit_storage();
rag_check( 1 === count( $GLOBALS['rag_test_dbdelta'] ), 'dbDelta ran' );
rag_check( str_contains( $GLOBALS['rag_test_dbdelta'][0], 'wp_rag_service_rate_limits' ), 'dbDelta received the prefixed table' );
rag_check( '1' === get_option( 'rag_service_rate_limit_schema' ), 'schema option is stored' );
$before = count( $GLOBALS['rag_test_dbdelta'] );
rag_service_maybe_install_rate_limit_storage();
rag_check( $before === count( $GLOBALS['rag_test_dbdelta'] ), 'a recorded schema skips table creation' );

$wpdb->found_table = null;
$GLOBALS['rag_test_options'] = array();
$GLOBALS['rag_test_dbdelta'] = array();
rag_service_install_rate_limit_storage();
rag_check( ! array_key_exists( 'rag_service_rate_limit_schema', $GLOBALS['rag_test_options'] ), 'a missing table leaves the schema option unset' );

$database = new RAG_Service_Wpdb_Rate_Limit_Database();
$limiter  = new RAG_Service_Rate_Limiter( $database );
$wpdb->queries = array();
$wpdb->prepares = array();
$wpdb->insert_affected = 2;
$decision = $limiter->reserve( 'search', 30, 1700000060 );
rag_check( is_array( $decision ) && true === $decision['allowed'], 'MySQL affected-row 2 is admitted by the stub' );
rag_check( 40 === $decision['retry_after'], 'retry_after at 1700000060 is 40 seconds' );
rag_check( 2 === count( $wpdb->prepares ), 'reserve and expiry are two statements' );
$insert = $wpdb->prepares[0][0];
rag_check( str_contains( $insert, 'ON DUPLICATE KEY UPDATE' ), 'reserve is an upsert' );
rag_check( str_contains( $insert, 'IF(request_count < %d, request_count + 1, request_count)' ), 'upsert increments only under the limit' );
rag_check( ! str_contains( $insert, 'SELECT' ), 'reserve has no SELECT' );
rag_check( array( 'search', 1700000040, 30 ) === $wpdb->prepares[0][1], 'reserve binds route, window, and limit' );
rag_check( str_contains( $wpdb->queries[1], 'DELETE FROM wp_rag_service_rate_limits WHERE window_start < %d' ), 'expired windows are deleted' );

$wpdb->queries = array();
$wpdb->insert_affected = 0;
$full = $limiter->reserve( 'answer', 10, 1700000060 );
rag_check( is_array( $full ) && false === $full['allowed'], 'MySQL affected-row 0 is exhausted by the stub' );

$wpdb->queries = array();
$wpdb->fail_insert = true;
rag_check( null === $limiter->reserve( 'search', 30, 1700000060 ), 'wpdb query failure is storage failure' );
rag_check( 1 === count( $wpdb->queries ), 'storage failure stops after the failed insert' );

$wpdb->prefix = 'wp bad';
rag_check( null === ( new RAG_Service_Wpdb_Rate_Limit_Database() )->reserve( 'search', 1700000040, 30 ), 'unsafe table prefix fails closed' );
$wpdb->prefix = 'wp_';
$wpdb->fail_insert = false;

rag_check( 30 === rag_service_configured_limit( 'search' ), 'search default is 30' );
rag_check( 10 === rag_service_configured_limit( 'answer' ), 'answer default is 10' );
rag_check( null === rag_service_configured_limit( 'other' ), 'unknown route has no limit' );

$acute = "\u{00E9}";
$emoji = "\u{1F600}";
$cluster = "e\u{0301}";
rag_check( 1 === rag_service_unicode_length( $acute ), 'precomposed é is one code point' );
rag_check( 2 === strlen( $acute ), 'precomposed é is two UTF-8 bytes' );
rag_check( 1 === rag_service_unicode_length( $emoji ), 'emoji is one code point' );
rag_check( 4 === strlen( $emoji ), 'emoji is four UTF-8 bytes' );
rag_check( 2 === rag_service_unicode_length( $cluster ), 'combining acute counts as its own code point' );
rag_check( 2 === rag_service_unicode_length_without_mbstring( $cluster ), 'mbstring fallback counts combining marks' );
rag_check( 1 === rag_service_unicode_length_without_mbstring( $emoji ), 'mbstring fallback counts emoji as one code point' );
rag_check( 2000 === RAG_Service_REST_Controller::QUERY_MAX_CHARACTERS, 'query max is 2000 code points' );

rag_group( '[sqlite-shared-storage] query checks happen before reservation or forwarding' );
$GLOBALS['rag_test_remote_response'] = rag_http( 200, '{"results":[{"text":"ok"}]}' );
list( $controller, $database, $clock, $path ) = rag_sqlite_controller( 1700000060 );

$cases = array(
	'search' => array( 'empty' => 'A search query is required.', 'method' => 'search' ),
	'answer' => array( 'empty' => 'A question is required.', 'method' => 'answer' ),
);
foreach ( $cases as $route => $case ) {
	foreach ( array( '', '   ', null, array( 'docs' ) ) as $query ) {
		$GLOBALS['rag_test_remote_posts'] = array();
		$result = $controller->{$case['method']}( new WP_REST_Request( array( 'query' => $query ) ) );
		rag_expect_error( $result, 400, $case['empty'], 'rag_service_invalid_query' );
		rag_expect_no_forward();
	}
	$GLOBALS['rag_test_remote_posts'] = array();
	$overlong = str_repeat( $acute, 2001 );
	$result = $controller->{$case['method']}( new WP_REST_Request( array( 'query' => $overlong ) ) );
	rag_expect_error( $result, 422, 'The query is too long.', 'rag_service_query_too_long' );
	rag_expect_no_forward();
	rag_check( ! str_contains( $result->get_error_message(), $acute ), $route . ' overlong message echoes the query' );
}
rag_check( array() === $database->rows(), 'rejected queries reserved no rows' );

$boundary = array(
	array( str_repeat( $acute, 2000 ), true ),
	array( str_repeat( $emoji, 2000 ), true ),
	array( str_repeat( $cluster, 1000 ), true ),
	array( str_repeat( $emoji, 2001 ), false ),
	array( str_repeat( $cluster, 1000 ) . "\u{0301}", false ),
);
foreach ( $boundary as $index => $item ) {
	$GLOBALS['rag_test_remote_posts'] = array();
	$result = $controller->search( new WP_REST_Request( array( 'query' => $item[0] ) ) );
	if ( $item[1] ) {
		rag_check( $result instanceof WP_REST_Response && 200 === $result->status, "boundary {$index} should forward" );
		$post = rag_last_post();
		$body = json_decode( $post['args']['body'], true );
		rag_check( $body['query'] === $item[0], "boundary {$index} forwards the original code points" );
	} else {
		rag_expect_error( $result, 422, 'The query is too long.', 'rag_service_query_too_long' );
		rag_expect_no_forward();
	}
}
rag_check( 3 === (int) $database->rows()[0]['request_count'], 'only forwarded boundary queries reserved slots' );

$GLOBALS['rag_test_remote_posts'] = array();
$trimmed = $controller->search( new WP_REST_Request( array( 'query' => '  visible-query  ' ) ) );
rag_check( $trimmed instanceof WP_REST_Response, 'trimmed query forwards' );
$trimmed_body = json_decode( rag_last_post()['args']['body'], true );
rag_check( 'visible-query' === $trimmed_body['query'], 'forwarded query is trimmed' );
rag_check( 5 === $trimmed_body['limit'], 'search still sends limit 5' );
rag_remove_sqlite( $database, $path );

rag_group( '[sqlite-shared-storage] site-wide exhaustion, separate routes, and window reset' );
list( $controller, $database, $clock, $path ) = rag_sqlite_controller( 1700000060 );
$_SERVER['HTTP_X_FORWARDED_FOR'] = '203.0.113.9';
$_SERVER['HTTP_CF_CONNECTING_IP'] = '198.51.100.8';
for ( $i = 0; $i < 30; $i++ ) {
	$GLOBALS['rag_test_remote_posts'] = array();
	$result = $controller->search( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
	rag_check( $result instanceof WP_REST_Response, "search {$i} admitted" );
}
$_SERVER['HTTP_X_FORWARDED_FOR'] = '203.0.113.10';
$GLOBALS['rag_test_remote_posts'] = array();
$limited = $controller->search( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
rag_expect_error( $limited, 429, 'Too many requests. Try again shortly.', 'rag_service_rate_limited' );
rag_expect_no_forward();
$retry_response = rag_service_send_retry_after( new WP_REST_Response( null, 429 ) );
rag_check( '40' === $retry_response->headers['Retry-After'], 'Retry-After is the remaining window' );
rag_check( 30 === (int) $database->rows()[0]['request_count'], 'rejected traffic left the stored count at 30' );

$GLOBALS['rag_test_remote_posts'] = array();
$answer = $controller->answer( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
rag_check( $answer instanceof WP_REST_Response, 'a full search window still admits ask' );
$answer_body = json_decode( rag_last_post()['args']['body'], true );
rag_check( array( 'query' ) === array_keys( $answer_body ), 'ask body is only the query' );
rag_check( 'http://rag.test/v1/answer' === $GLOBALS['rag_test_remote_posts'][0]['url'], 'ask URL' );

$clock->now = 1700000100;
$GLOBALS['rag_test_remote_posts'] = array();
$reset = $controller->search( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
rag_check( $reset instanceof WP_REST_Response, 'the next minute admits search again' );
$rows = $database->rows();
rag_check( 1 === count( $rows ), 'expired windows are removed' );
rag_check( 'search' === $rows[0]['route'] && '1700000100' === (string) $rows[0]['window_start'], 'only the new search window remains' );
rag_check( 1 === (int) $rows[0]['request_count'], 'the new window starts at one' );
rag_remove_sqlite( $database, $path );
unset( $_SERVER['HTTP_X_FORWARDED_FOR'], $_SERVER['HTTP_CF_CONNECTING_IP'] );

list( $controller, $database, $clock, $path ) = rag_sqlite_controller( 1700000060 );
for ( $i = 0; $i < 10; $i++ ) {
	$result = $controller->answer( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
	rag_check( $result instanceof WP_REST_Response, "answer {$i} admitted" );
}
$GLOBALS['rag_test_remote_posts'] = array();
$answer_limited = $controller->answer( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
rag_expect_error( $answer_limited, 429, 'Too many requests. Try again shortly.', 'rag_service_rate_limited' );
rag_expect_no_forward();
$still_search = $controller->search( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
rag_check( $still_search instanceof WP_REST_Response, 'a full ask window still admits search' );
rag_remove_sqlite( $database, $path );

rag_group( '[sqlite-shared-storage] forwarded failures consume a slot; storage failure does not forward' );
list( $controller, $database, $clock, $path ) = rag_sqlite_controller( 1700000060 );
$GLOBALS['rag_test_remote_response'] = rag_http( 500, '{"message":"detail-token rag-test-key-do-not-leak"}' );
for ( $i = 0; $i < 30; $i++ ) {
	$GLOBALS['rag_test_remote_posts'] = array();
	$failed = $controller->search( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
	rag_expect_error( $failed, 503, 'Search is temporarily unavailable.', 'rag_service_search_unavailable' );
	rag_check( 1 === count( $GLOBALS['rag_test_remote_posts'] ), 'the failed attempt was forwarded' );
}
$GLOBALS['rag_test_remote_posts'] = array();
$after_failures = $controller->search( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
rag_expect_error( $after_failures, 429, 'Too many requests. Try again shortly.', 'rag_service_rate_limited' );
rag_expect_no_forward();
rag_check( 30 === (int) $database->rows()[0]['request_count'], 'failed forwards counted toward the limit' );
rag_remove_sqlite( $database, $path );

$missing_path = rag_temp_path( 'rag-missing-' );
$missing      = new Rag_Sqlite_Rate_Limit_Database( $missing_path );
$controller   = new RAG_Service_REST_Controller( new RAG_Service_Rate_Limiter( $missing ) );
$GLOBALS['rag_test_remote_posts'] = array();
$storage_error = $controller->search( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
rag_expect_error( $storage_error, 503, 'Search is temporarily unavailable.', 'rag_service_search_unavailable' );
rag_expect_no_forward();
$storage_answer = $controller->answer( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
rag_expect_error( $storage_answer, 503, 'Answer generation is temporarily unavailable.', 'rag_service_answer_unavailable' );
rag_remove_sqlite( $missing, $missing_path );
$quiet = rag_service_send_retry_after( new WP_REST_Response( null, 503 ) );
rag_check( array() === $quiet->headers, 'storage failure omits Retry-After' );

rag_group( '[wordpress-stubs] upstream 413 and 422 stay visible; other failures stay generic' );
list( $controller, $database, $clock, $path ) = rag_sqlite_controller( 1700000060 );
$leak = '{"error":{"message":"detail-token rag-test-key-do-not-leak visible-query"}}';
$upstream = array(
	array( 'search', 413, 'not-json rag-test-key-do-not-leak visible-query', 413, 'The request is too large.', 'rag_service_request_too_large' ),
	array( 'answer', 413, $leak, 413, 'The request is too large.', 'rag_service_request_too_large' ),
	array( 'search', 422, $leak, 422, "The request couldn't be processed.", 'rag_service_request_rejected' ),
	array( 'answer', 422, $leak, 422, "The request couldn't be processed.", 'rag_service_request_rejected' ),
	array( 'search', 302, $leak, 503, 'Search is temporarily unavailable.', 'rag_service_search_unavailable' ),
	array( 'answer', 307, '{"results":[{"text":"detail-token"}]}', 503, 'Answer generation is temporarily unavailable.', 'rag_service_answer_unavailable' ),
	array( 'search', 401, $leak, 503, 'Search is temporarily unavailable.', 'rag_service_search_unavailable' ),
	array( 'answer', 503, '{"message":"detail-token"}', 503, 'Answer generation is temporarily unavailable.', 'rag_service_answer_unavailable' ),
	array( 'search', 200, 'not-json', 503, 'Search is temporarily unavailable.', 'rag_service_search_unavailable' ),
	array( 'search', 500, '<html>rag-test-key-do-not-leak detail-token</html>', 503, 'Search is temporarily unavailable.', 'rag_service_search_unavailable' ),
);
foreach ( $upstream as $item ) {
	$GLOBALS['rag_test_remote_posts']    = array();
	$GLOBALS['rag_test_remote_handler']  = null;
	$GLOBALS['rag_test_remote_response'] = rag_http( $item[1], $item[2] );
	$result = $controller->{$item[0]}( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
	rag_expect_error( $result, $item[3], $item[4], $item[5] );
	$post = rag_last_post();
	rag_check( 0 === $post['args']['redirection'], 'redirection is disabled' );
	rag_check( true === $post['args']['sslverify'], 'TLS verification stays on' );
	rag_check( 15 === $post['args']['timeout'], 'timeout stays 15 seconds' );
	rag_check( 'rag-test-key-do-not-leak' === $post['args']['headers']['X-API-Key'], 'API key stays on the server request' );
	rag_check( ! str_contains( wp_json_encode( rag_visitor_json( $result ) ), 'rag-test-key-do-not-leak' ), 'visitor JSON contains the API key' );
	rag_check( ! str_contains( wp_json_encode( rag_visitor_json( $result ) ), 'detail-token' ), 'visitor JSON contains an upstream detail' );
}
$GLOBALS['rag_test_remote_handler'] = static function () {
	return new WP_Error( 'http_request_failed', 'cURL error 28 timed out rag-test-key-do-not-leak visible-query detail-token' );
};
foreach ( array( 'search', 'answer' ) as $route ) {
	$GLOBALS['rag_test_remote_posts'] = array();
	$result = $controller->{$route}( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
	$message = 'search' === $route ? 'Search is temporarily unavailable.' : 'Answer generation is temporarily unavailable.';
	$code = 'search' === $route ? 'rag_service_search_unavailable' : 'rag_service_answer_unavailable';
	rag_expect_error( $result, 503, $message, $code );
	rag_check( 1 === count( $GLOBALS['rag_test_remote_posts'] ), $route . ' transport failure was attempted' );
	rag_check( ! str_contains( $result->get_error_message(), 'cURL' ), $route . ' exposes the transport exception' );
}
unset( $GLOBALS['rag_test_remote_handler'] );
$GLOBALS['rag_test_remote_response'] = rag_http( 200, '{"results":[{"text":"ok"}]}' );
$GLOBALS['rag_test_remote_posts'] = array();
$success = $controller->search( new WP_REST_Request( array( 'query' => 'visible-query' ) ) );
rag_check( $success instanceof WP_REST_Response && array( array( 'text' => 'ok' ) ) === $success->data['results'], 'successful search is returned' );
$post = rag_last_post();
rag_check( 'http://rag.test/v1/search' === $post['url'], 'trailing slash is removed from the origin' );
rag_check( 0 === $post['args']['redirection'], 'successful calls also disable redirects' );
rag_remove_sqlite( $database, $path );

rag_group( '[client-script] the browser shows the fixed message and does not retry' );
$script = (string) file_get_contents( dirname( __DIR__ ) . '/assets/rag-search.js' );
rag_check( 1 === substr_count( $script, 'fetch(' ), 'the script sends one request' );
rag_check( str_contains( $script, 'data.message' ), 'the script displays the REST message' );
rag_check( str_contains( $script, 'button.disabled = false' ), 'the script re-enables the buttons' );
$disabled_at = strpos( $script, 'button.disabled = true' );
$enabled_at  = strpos( $script, 'button.disabled = false' );
rag_check( false !== $disabled_at && false !== $enabled_at && $enabled_at > $disabled_at, 'buttons are enabled after the request' );
rag_check( ! str_contains( $script, 'setTimeout' ) && ! str_contains( $script, 'setInterval' ), 'the script has no retry timer' );

rag_group( '[fresh-process] invalid settings fail closed; positive settings change the limits' );
rag_check(
	"search 500 0 The RAG service URL isn't configured.\nanswer 500 0 The RAG service URL isn't configured." === rag_settings_scenario( 'missing-config' ),
	'missing configuration'
);
foreach ( array( 'search-zero', 'search-negative', 'search-float', 'search-string', 'search-true' ) as $scenario ) {
	rag_check(
		'search 503 0 Search is temporarily unavailable.' === rag_settings_scenario( $scenario ),
		$scenario
	);
}
rag_check(
	"answer 503 0 Answer generation is temporarily unavailable.\nsearch-still-works 200 1 ok" === rag_settings_scenario( 'answer-string-search-default' ),
	'an invalid ask limit leaves search available'
);
rag_check(
	'custom 200:1,200:1,429:0,200:1,429:0' === rag_settings_scenario( 'custom-limits' ),
	'configured limits of 2 and 1'
);

rag_group( '[sqlite-shared-storage-concurrent-processes] forty processes share one counter' );
$race_path = rag_temp_path( 'rag-race-' );
$race_db   = new Rag_Sqlite_Rate_Limit_Database( $race_path );
$race_db->create_table();
$race_db->close();
unset( $race_db );
$processes = array();
for ( $i = 0; $i < 40; $i++ ) {
	$pipes = array();
	$process = proc_open(
		array( PHP_BINARY, __DIR__ . '/concurrency-worker.php', $race_path, 'search', '10', '1700000060' ),
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
$counts = array_count_values( $outcomes );
rag_check( 10 === ( $counts['admitted'] ?? 0 ), 'concurrent admitted ' . ( $counts['admitted'] ?? 0 ) . ' of 10' );
rag_check( 30 === ( $counts['exhausted'] ?? 0 ), 'concurrent exhausted ' . ( $counts['exhausted'] ?? 0 ) . ' of 30' );
rag_check( 0 === ( $counts['failed'] ?? 0 ), 'concurrent storage failures ' . ( $counts['failed'] ?? 0 ) );
$race_db = new Rag_Sqlite_Rate_Limit_Database( $race_path );
$race_rows = $race_db->rows();
rag_check( 1 === count( $race_rows ) && 10 === (int) $race_rows[0]['request_count'], 'shared row stopped at the limit' );
rag_remove_sqlite( $race_db, $race_path );

echo $rag_test_checks . " checks, " . count( $rag_test_failures ) . " failed\n";
exit( array() === $rag_test_failures ? 0 : 1 );
