<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Client for communicating with the Python RAG Service API.
 */
class DL_RAG_API_Client {

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
				'timeout' => 15,
				'headers' => array(
					'Content-Type' => 'application/json',
                    'X-API-Key'    => $this->api_key,
				),
				'body' => wp_json_encode( $body ),
			)
		);

		if ( is_wp_error( $response ) ) {
			return $response;
		}

		$status_code = wp_remote_retrieve_response_code( $response );
		$response_body = wp_remote_retrieve_body( $response );
		$data = json_decode( $response_body, true );

		if ( ! is_array( $data ) ) {
			return new WP_Error(
				'dl_rag_invalid_response',
				'The RAG service returned an invalid response.'
			);
		}

		if ( $status_code < 200 || $status_code >= 300 ) {
			return new WP_Error(
				'dl_rag_api_error',
				'The RAG service returned an error.',
				array(
					'status' => $status_code,
					'response' => $data,
				)
			);
		}

		return $data;
	}
}