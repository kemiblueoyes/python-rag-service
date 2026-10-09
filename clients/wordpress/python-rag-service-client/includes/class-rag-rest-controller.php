<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Exposes the RAG client through the WordPress REST API.
 */
class RAG_Service_REST_Controller {

	public const QUERY_MAX_CHARACTERS = 2000;

	/**
	 * Seconds until the current rate-limit window ends.
	 *
	 * @var int|null
	 */
	private static ?int $retry_after = null;

	/**
	 * Shared limiter. Production builds a database-backed limiter on first use.
	 *
	 * @var RAG_Service_Rate_Limiter|null
	 */
	private ?RAG_Service_Rate_Limiter $limiter;

	/**
	 * Clock used for the rate-limit window.
	 *
	 * @var callable
	 */
	private $clock;

	/**
	 * Create the controller.
	 *
	 * @param RAG_Service_Rate_Limiter|null $limiter Shared limiter.
	 * @param callable|null                 $clock   Unix-time source.
	 */
	public function __construct( ?RAG_Service_Rate_Limiter $limiter = null, ?callable $clock = null ) {
		$this->limiter = $limiter;
		$this->clock   = $clock ?? static function (): int {
			return time();
		};
	}

	/**
	 * Take and clear the pending Retry-After value.
	 *
	 * @return int|null
	 */
	public static function take_retry_after(): ?int {
		$retry_after       = self::$retry_after;
		self::$retry_after = null;
		return $retry_after;
	}

	/**
	 * Register WordPress REST routes.
	 */
	public function register_routes() {
		register_rest_route(
			'python-rag-service/v1',
			'/search',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'search' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'query' => array(
						'required'          => true,
						'type'              => 'string',
						'sanitize_callback' => 'sanitize_text_field',
					),
				),
			)
		);

		register_rest_route(
			'python-rag-service/v1',
			'/answer',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'answer' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'query' => array(
						'required'          => true,
						'type'              => 'string',
						'sanitize_callback' => 'sanitize_text_field',
					),
				),
			)
		);
	}

	/**
	 * Proxy a search request to the Python RAG service.
	 *
	 * @param WP_REST_Request $request WordPress REST request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function search( WP_REST_Request $request ) {
		return $this->proxy( $request, 'search' );
	}

	/**
	 * Proxy an answer request to the Python RAG service.
	 *
	 * @param WP_REST_Request $request WordPress REST request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function answer( WP_REST_Request $request ) {
		return $this->proxy( $request, 'answer' );
	}

	/**
	 * Validate, reserve, and forward one public request.
	 *
	 * Query checks run before a rate-limit slot is reserved. A reserved slot
	 * counts even when Python later fails.
	 *
	 * @param WP_REST_Request $request WordPress REST request.
	 * @param string          $route   `search` or `answer`.
	 * @return WP_REST_Response|WP_Error
	 */
	private function proxy( WP_REST_Request $request, string $route ) {
		self::$retry_after = null;

		if ( ! defined( 'RAG_SERVICE_API_BASE_URL' ) || ! defined( 'RAG_SERVICE_API_KEY' ) ) {
			return new WP_Error(
				'rag_service_not_configured',
				"The RAG service URL isn't configured.",
				array( 'status' => 500 )
			);
		}

		$param = $request->get_param( 'query' );
		if ( ! is_string( $param ) ) {
			$param = '';
		}
		$query = trim( $param );

		if ( '' === $query ) {
			return new WP_Error(
				'rag_service_invalid_query',
				'search' === $route ? 'A search query is required.' : 'A question is required.',
				array( 'status' => 400 )
			);
		}

		$length = rag_service_unicode_length( $query );
		if ( null === $length ) {
			return $this->unavailable( $route );
		}
		if ( $length > self::QUERY_MAX_CHARACTERS ) {
			return new WP_Error(
				'rag_service_query_too_long',
				'The query is too long.',
				array( 'status' => 422 )
			);
		}

		$limit = rag_service_configured_limit( $route );
		if ( null === $limit ) {
			return $this->unavailable( $route );
		}

		$decision = $this->limiter()->reserve( $route, $limit, (int) ( $this->clock )() );
		if ( null === $decision ) {
			return $this->unavailable( $route );
		}
		if ( ! $decision['allowed'] ) {
			self::$retry_after = $decision['retry_after'];
			return new WP_Error(
				'rag_service_rate_limited',
				'Too many requests. Try again shortly.',
				array( 'status' => 429 )
			);
		}

		$client = new RAG_Service_API_Client(
			RAG_SERVICE_API_BASE_URL,
			RAG_SERVICE_API_KEY
		);
		$result = 'search' === $route ? $client->search( $query ) : $client->answer( $query );
		if ( is_wp_error( $result ) ) {
			return $this->map_upstream_error( $result, $route );
		}

		return new WP_REST_Response( $result, 200 );
	}

	/**
	 * Limiter for this controller.
	 *
	 * @return RAG_Service_Rate_Limiter
	 */
	private function limiter(): RAG_Service_Rate_Limiter {
		if ( null === $this->limiter ) {
			$this->limiter = new RAG_Service_Rate_Limiter( new RAG_Service_Wpdb_Rate_Limit_Database() );
		}

		return $this->limiter;
	}

	/**
	 * Map a Python or transport failure to a visitor response.
	 *
	 * Upstream 413 and 422 keep those statuses. The visitor message is fixed
	 * and doesn't include the Python body, the query, or the API key.
	 *
	 * @param WP_Error $error Upstream or transport error.
	 * @param string   $route `search` or `answer`.
	 * @return WP_Error
	 */
	private function map_upstream_error( WP_Error $error, string $route ): WP_Error {
		$code = $error->get_error_code();
		if ( 'rag_service_upstream_too_large' === $code ) {
			return new WP_Error(
				'rag_service_request_too_large',
				'The request is too large.',
				array( 'status' => 413 )
			);
		}
		if ( 'rag_service_upstream_rejected' === $code ) {
			return new WP_Error(
				'rag_service_request_rejected',
				"The request couldn't be processed.",
				array( 'status' => 422 )
			);
		}

		return $this->unavailable( $route );
	}

	/**
	 * Generic unavailable response for one route.
	 *
	 * @param string $route `search` or `answer`.
	 * @return WP_Error
	 */
	private function unavailable( string $route ): WP_Error {
		if ( 'answer' === $route ) {
			return new WP_Error(
				'rag_service_answer_unavailable',
				'Answer generation is temporarily unavailable.',
				array( 'status' => 503 )
			);
		}

		return new WP_Error(
			'rag_service_search_unavailable',
			'Search is temporarily unavailable.',
			array( 'status' => 503 )
		);
	}
}

/**
 * Add Retry-After to a rate-limited REST response.
 *
 * @param mixed $response REST response.
 * @return mixed
 */
function rag_service_send_retry_after( $response ) {
	if ( ! is_object( $response ) || ! method_exists( $response, 'get_status' ) || ! method_exists( $response, 'header' ) ) {
		return $response;
	}
	if ( 429 !== (int) $response->get_status() ) {
		return $response;
	}

	$retry_after = RAG_Service_REST_Controller::take_retry_after();
	if ( null !== $retry_after ) {
		$response->header( 'Retry-After', (string) $retry_after );
	}

	return $response;
}
