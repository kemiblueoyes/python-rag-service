<?php
/**
 * WordPress function and class stubs for the plugin tests.
 *
 * These stand in for WordPress. They don't open a database and they don't
 * follow HTTP redirects.
 */

if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', dirname( __DIR__ ) . '/' );
}

if ( ! function_exists( 'plugin_dir_path' ) ) {
	function plugin_dir_path( $file ) {
		return rtrim( dirname( $file ), '/' ) . '/';
	}
}

if ( ! function_exists( 'plugin_dir_url' ) ) {
	function plugin_dir_url( $file ) {
		return 'https://wordpress.test/wp-content/plugins/python-rag-service-client/';
	}
}

if ( ! function_exists( 'add_action' ) ) {
	function add_action( $hook, $callback, $priority = 10, $accepted_args = 1 ) {
		$GLOBALS['rag_test_hooks'][] = array( 'action', $hook, $callback, $priority, $accepted_args );
	}
}

if ( ! function_exists( 'add_filter' ) ) {
	function add_filter( $hook, $callback, $priority = 10, $accepted_args = 1 ) {
		$GLOBALS['rag_test_hooks'][] = array( 'filter', $hook, $callback, $priority, $accepted_args );
	}
}

if ( ! function_exists( 'add_shortcode' ) ) {
	function add_shortcode( $tag, $callback ) {
		$GLOBALS['rag_test_shortcodes'][ $tag ] = $callback;
	}
}

if ( ! function_exists( 'register_activation_hook' ) ) {
	function register_activation_hook( $file, $callback ) {
		$GLOBALS['rag_test_activation'] = $callback;
	}
}

if ( ! function_exists( 'register_rest_route' ) ) {
	function register_rest_route( $namespace, $route, $args ) {
		$GLOBALS['rag_test_routes'][] = array( $namespace, $route, $args );
	}
}

if ( ! function_exists( 'untrailingslashit' ) ) {
	function untrailingslashit( $value ) {
		return rtrim( (string) $value, '/' );
	}
}

if ( ! function_exists( 'wp_json_encode' ) ) {
	function wp_json_encode( $data ) {
		return json_encode( $data );
	}
}

if ( ! function_exists( 'is_wp_error' ) ) {
	function is_wp_error( $thing ) {
		return $thing instanceof WP_Error;
	}
}

if ( ! function_exists( 'wp_remote_post' ) ) {
	function wp_remote_post( $url, $args = array() ) {
		$GLOBALS['rag_test_remote_posts'][] = array(
			'url'  => $url,
			'args' => $args,
		);
		if ( isset( $GLOBALS['rag_test_remote_handler'] ) && is_callable( $GLOBALS['rag_test_remote_handler'] ) ) {
			return call_user_func( $GLOBALS['rag_test_remote_handler'], $url, $args );
		}
		return $GLOBALS['rag_test_remote_response'];
	}
}

if ( ! function_exists( 'wp_remote_retrieve_response_code' ) ) {
	function wp_remote_retrieve_response_code( $response ) {
		if ( is_array( $response ) && isset( $response['response']['code'] ) ) {
			return $response['response']['code'];
		}
		return 0;
	}
}

if ( ! function_exists( 'wp_remote_retrieve_body' ) ) {
	function wp_remote_retrieve_body( $response ) {
		if ( is_array( $response ) && isset( $response['body'] ) ) {
			return $response['body'];
		}
		return '';
	}
}

if ( ! function_exists( 'get_option' ) ) {
	function get_option( $name, $default = false ) {
		if ( array_key_exists( $name, $GLOBALS['rag_test_options'] ) ) {
			return $GLOBALS['rag_test_options'][ $name ];
		}
		return $default;
	}
}

if ( ! function_exists( 'update_option' ) ) {
	function update_option( $name, $value ) {
		$GLOBALS['rag_test_options'][ $name ] = $value;
		return true;
	}
}

if ( ! function_exists( 'dbDelta' ) ) {
	function dbDelta( $sql ) {
		$GLOBALS['rag_test_dbdelta'][] = $sql;
		return array();
	}
}

if ( ! class_exists( 'WP_Error' ) ) {
	class WP_Error {
		public string $code;
		public string $message;
		public mixed $data;

		public function __construct( $code = '', $message = '', $data = null ) {
			$this->code    = (string) $code;
			$this->message = (string) $message;
			$this->data    = $data;
		}

		public function get_error_code() {
			return $this->code;
		}

		public function get_error_message() {
			return $this->message;
		}

		public function get_error_data() {
			return $this->data;
		}
	}
}

if ( ! class_exists( 'WP_REST_Request' ) ) {
	class WP_REST_Request {
		public array $params;

		public function __construct( $params = array() ) {
			$this->params = $params;
		}

		public function get_param( $key ) {
			if ( array_key_exists( $key, $this->params ) ) {
				return $this->params[ $key ];
			}
			return null;
		}
	}
}

if ( ! class_exists( 'WP_REST_Response' ) ) {
	class WP_REST_Response {
		public mixed $data;
		public int $status;
		public array $headers;

		public function __construct( $data = null, $status = 200 ) {
			$this->data    = $data;
			$this->status  = (int) $status;
			$this->headers = array();
		}

		public function get_status() {
			return $this->status;
		}

		public function header( $key, $value ) {
			$this->headers[ $key ] = $value;
		}
	}
}

$GLOBALS['rag_test_hooks']         = array();
$GLOBALS['rag_test_shortcodes']    = array();
$GLOBALS['rag_test_routes']        = array();
$GLOBALS['rag_test_remote_posts']  = array();
$GLOBALS['rag_test_remote_response'] = array(
	'response' => array( 'code' => 200 ),
	'body'     => '{"results":[]}',
);
$GLOBALS['rag_test_options']       = array();
$GLOBALS['rag_test_dbdelta']       = array();
