<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Client for communicating with the Python RAG Service API.
 */
class RAG_Service_API_Client {

    /**
     * API key for authenticating with the Python RAG service.
     *
     * @var string
     */
    private string $api_key;


	/**
	 * Base URL for the Python RAG service.
	 *
	 * @var string
	 */
	private string $base_url;

	/**
	 * Create the API client.
	 *
	 * @param string $base_url Base URL for the Python RAG service.
	 */
	public function __construct( string $base_url, string $api_key) {
		$this->base_url = untrailingslashit( $base_url );
        $this->api_key  = $api_key;
	}

	/**
	 * Search indexed documentation.
	 *
	 * @param string $query   Search query.
	 * @param array  $filters Optional metadata filters.
	 * @param int    $limit   Maximum number of results.
	 *
	 * @return array|WP_Error
	 */
	public function search(
		string $query,
		array $filters = array(),
		int $limit = 5
	) {
		$body = array(
			'query' => $query,
			'limit' => $limit,
		);

		if ( ! empty( $filters ) ) {
			$body['filters'] = $filters;
		}

		return $this->post( '/v1/search', $body );
	}

	/**
	 * Generate a grounded answer.
	 *
	 * @param string $query   Question to answer.
	 * @param array  $filters Optional metadata filters.
	 *
	 * @return array|WP_Error
	 */
	public function answer(
		string $query,
		array $filters = array()
	) {
		$body = array(
			'query' => $query,
		);

		if ( ! empty( $filters ) ) {
			$body['filters'] = $filters;
		}

		return $this->post( '/v1/answer', $body );
	}

	/**
	 * Send a POST request to the RAG service.
	 *
	 * @param string $endpoint API endpoint.
	 * @param array  $body     Request body.
	 *
	 * @return array|WP_Error
	 */
	private function post( string $endpoint, array $body ) {
		$response = wp_remote_post(
			$this->base_url . $endpoint,
			array(
				'timeout'     => 15,
				'redirection' => 0,
				'sslverify'   => true,
				'headers'     => array(
					'Content-Type' => 'application/json',
					'X-API-Key'    => $this->api_key,
				),
				'body'        => wp_json_encode( $body ),
			)
		);

		if ( is_wp_error( $response ) ) {
			return new WP_Error(
				'rag_service_transport_failed',
				'The RAG service request failed.'
			);
		}

		$status_code = (int) wp_remote_retrieve_response_code( $response );
		if ( $status_code >= 300 && $status_code < 400 ) {
			return new WP_Error(
				'rag_service_redirected',
				'The RAG service request failed.'
			);
		}
		if ( 413 === $status_code ) {
			return new WP_Error(
				'rag_service_upstream_too_large',
				'The RAG service request failed.'
			);
		}
		if ( 422 === $status_code ) {
			return new WP_Error(
				'rag_service_upstream_rejected',
				'The RAG service request failed.'
			);
		}

		$data = json_decode( (string) wp_remote_retrieve_body( $response ), true );
		if ( ! is_array( $data ) || $status_code < 200 || $status_code >= 300 ) {
			return new WP_Error(
				'rag_service_upstream_failed',
				'The RAG service request failed.'
			);
		}

		return $data;
	}
}