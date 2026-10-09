<?php
/**
 * Plugin behavior in a fresh process so rate-limit constants can be defined once.
 *
 * Usage: php settings-worker.php <scenario>
 */

require_once __DIR__ . '/wp-stubs.php';

$scenario = $argv[1] ?? '';

switch ( $scenario ) {
	case 'missing-config':
		break;
	case 'search-zero':
		define( 'RAG_SERVICE_API_BASE_URL', 'http://rag.test' );
		define( 'RAG_SERVICE_API_KEY', 'rag-test-key-do-not-leak' );
		define( 'RAG_SERVICE_SEARCH_REQUESTS_PER_MINUTE', 0 );
		break;
	case 'search-negative':
		define( 'RAG_SERVICE_API_BASE_URL', 'http://rag.test' );
		define( 'RAG_SERVICE_API_KEY', 'rag-test-key-do-not-leak' );
		define( 'RAG_SERVICE_SEARCH_REQUESTS_PER_MINUTE', -3 );
		break;
	case 'search-float':
		define( 'RAG_SERVICE_API_BASE_URL', 'http://rag.test' );
		define( 'RAG_SERVICE_API_KEY', 'rag-test-key-do-not-leak' );
		define( 'RAG_SERVICE_SEARCH_REQUESTS_PER_MINUTE', 30.0 );
		break;
	case 'search-string':
		define( 'RAG_SERVICE_API_BASE_URL', 'http://rag.test' );
		define( 'RAG_SERVICE_API_KEY', 'rag-test-key-do-not-leak' );
		define( 'RAG_SERVICE_SEARCH_REQUESTS_PER_MINUTE', '30' );
		break;
	case 'search-true':
		define( 'RAG_SERVICE_API_BASE_URL', 'http://rag.test' );
		define( 'RAG_SERVICE_API_KEY', 'rag-test-key-do-not-leak' );
		define( 'RAG_SERVICE_SEARCH_REQUESTS_PER_MINUTE', true );
		break;
	case 'answer-string-search-default':
		define( 'RAG_SERVICE_API_BASE_URL', 'http://rag.test' );
		define( 'RAG_SERVICE_API_KEY', 'rag-test-key-do-not-leak' );
		define( 'RAG_SERVICE_ANSWER_REQUESTS_PER_MINUTE', '10' );
		break;
	case 'custom-limits':
		define( 'RAG_SERVICE_API_BASE_URL', 'http://rag.test' );
		define( 'RAG_SERVICE_API_KEY', 'rag-test-key-do-not-leak' );
		define( 'RAG_SERVICE_SEARCH_REQUESTS_PER_MINUTE', 2 );
		define( 'RAG_SERVICE_ANSWER_REQUESTS_PER_MINUTE', 1 );
		break;
	default:
		fwrite( STDERR, "Unknown scenario {$scenario}\n" );
		exit( 2 );
}

require_once dirname( __DIR__ ) . '/python-rag-service-client.php';
require_once __DIR__ . '/sqlite-rate-limit-database.php';

/**
 * Database that fails the test if a request is reserved.
 */
class Rag_Exploding_Rate_Limit_Database implements RAG_Service_Rate_Limit_Database {
	public function reserve( string $route, int $window_start, int $limit ): ?bool {
		throw new RuntimeException( 'reserved ' . $route );
	}

	public function delete_windows_before( int $window_start ): void {
	}
}

/**
 * Print status, whether Python was called, and the visitor message.
 *
 * @param mixed  $result   Controller result.
 * @param string $label    Case label.
 */
function rag_settings_report( $result, string $label ): void {
	$status  = is_wp_error( $result ) ? (int) $result->get_error_data()['status'] : (int) $result->status;
	$forward = count( $GLOBALS['rag_test_remote_posts'] );
	$message = is_wp_error( $result ) ? $result->get_error_message() : 'ok';
	echo $label . ' ' . $status . ' ' . $forward . ' ' . $message . "\n";
}

if ( 'missing-config' === $scenario ) {
	$controller = new RAG_Service_REST_Controller( new RAG_Service_Rate_Limiter( new Rag_Exploding_Rate_Limit_Database() ) );
	rag_settings_report( $controller->search( new WP_REST_Request( array( 'query' => 'docs' ) ) ), 'search' );
	rag_settings_report( $controller->answer( new WP_REST_Request( array( 'query' => 'docs' ) ) ), 'answer' );
	exit( 0 );
}

if ( in_array( $scenario, array( 'search-zero', 'search-negative', 'search-float', 'search-string', 'search-true' ), true ) ) {
	$controller = new RAG_Service_REST_Controller( new RAG_Service_Rate_Limiter( new Rag_Exploding_Rate_Limit_Database() ) );
	rag_settings_report( $controller->search( new WP_REST_Request( array( 'query' => 'docs' ) ) ), 'search' );
	exit( 0 );
}

if ( 'answer-string-search-default' === $scenario ) {
	$controller = new RAG_Service_REST_Controller( new RAG_Service_Rate_Limiter( new Rag_Exploding_Rate_Limit_Database() ) );
	rag_settings_report( $controller->answer( new WP_REST_Request( array( 'query' => 'docs' ) ) ), 'answer' );

	if ( ! is_dir( __DIR__ . '/tmp' ) ) {
		mkdir( __DIR__ . '/tmp', 0700, true );
	}
	$sqlite_path = tempnam( __DIR__ . '/tmp', 'rag-answer-invalid-' );
	$database    = new Rag_Sqlite_Rate_Limit_Database( $sqlite_path );
	$database->create_table();
	$search = new RAG_Service_REST_Controller( new RAG_Service_Rate_Limiter( $database ) );
	$GLOBALS['rag_test_remote_posts'] = array();
	rag_settings_report( $search->search( new WP_REST_Request( array( 'query' => 'docs' ) ) ), 'search-still-works' );
	unset( $database );
	foreach ( array( $sqlite_path, $sqlite_path . '-wal', $sqlite_path . '-shm' ) as $file ) {
		if ( is_file( $file ) ) {
			unlink( $file );
		}
	}
	exit( 0 );
}

if ( 'custom-limits' === $scenario ) {
	if ( ! is_dir( __DIR__ . '/tmp' ) ) {
		mkdir( __DIR__ . '/tmp', 0700, true );
	}
	$path     = tempnam( __DIR__ . '/tmp', 'rag-custom-' );
	$database = new Rag_Sqlite_Rate_Limit_Database( $path );
	$database->create_table();
	$clock = static function (): int {
		return 1700000060;
	};
	$controller = new RAG_Service_REST_Controller( new RAG_Service_Rate_Limiter( $database ), $clock );
	$statuses   = array();
	foreach ( array( 'search', 'search', 'search' ) as $route ) {
		$GLOBALS['rag_test_remote_posts'] = array();
		$result = $controller->search( new WP_REST_Request( array( 'query' => 'docs' ) ) );
		$statuses[] = ( is_wp_error( $result ) ? $result->get_error_data()['status'] : $result->status )
			. ':' . count( $GLOBALS['rag_test_remote_posts'] );
	}
	foreach ( array( 'answer', 'answer' ) as $unused ) {
		$GLOBALS['rag_test_remote_posts'] = array();
		$result = $controller->answer( new WP_REST_Request( array( 'query' => 'docs' ) ) );
		$statuses[] = ( is_wp_error( $result ) ? $result->get_error_data()['status'] : $result->status )
			. ':' . count( $GLOBALS['rag_test_remote_posts'] );
	}
	unset( $database );
	foreach ( array( $path, $path . '-wal', $path . '-shm' ) as $file ) {
		if ( is_file( $file ) ) {
			unlink( $file );
		}
	}
	echo 'custom ' . implode( ',', $statuses ) . "\n";
	exit( 0 );
}

fwrite( STDERR, "Scenario {$scenario} didn't finish\n" );
exit( 2 );
