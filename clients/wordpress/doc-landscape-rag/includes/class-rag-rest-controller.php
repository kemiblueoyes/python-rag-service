<?php

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Exposes the RAG client through the WordPress REST API.
 */
class DL_RAG_REST_Controller {

    /**
     * Register WordPress REST routes.
     */
    public function register_routes() {
        register_rest_route(
            'doc-landscape-rag/v1',
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
            'doc-landscape-rag/v1',
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
	 *
	 * @return WP_REST_Response|WP_Error
	 */
	public function search( WP_REST_Request $request ) {
		if ( ! defined( 'DL_RAG_API_BASE_URL' ) || ! defined( 'DL_RAG_API_KEY' ) ) {
			return new WP_Error(
				'dl_rag_not_configured',
				'The RAG service URL is not configured.',
				array( 'status' => 500 )
			);
		}

		$query = trim( (string) $request->get_param( 'query' ) );

		if ( '' === $query ) {
			return new WP_Error(
				'dl_rag_invalid_query',
				'A search query is required.',
				array( 'status' => 400 )
			);
		}

		$client = new DL_RAG_API_Client(
            DL_RAG_API_BASE_URL,
            DL_RAG_API_KEY
        );
        $result = $client->search( $query );

        if ( is_wp_error( $result ) ) {
            return new WP_Error(
                'dl_rag_search_unavailable',
                'Search is temporarily unavailable.',
                array( 'status' => 503 )
            );
        }
        
        return new WP_REST_Response( $result, 200 );
	}

    /**
     * Proxy an answer request to the Python RAG service.
     *
     * @param WP_REST_Request $request WordPress REST request.
     *
     * @return WP_REST_Response|WP_Error
     */
    public function answer( WP_REST_Request $request ) {
        if ( ! defined( 'DL_RAG_API_BASE_URL' ) || ! defined( 'DL_RAG_API_KEY' ) ) {
            return new WP_Error(
                'dl_rag_not_configured',
                'The RAG service URL is not configured.',
                array( 'status' => 500 )
            );
        }

        $query = trim( (string) $request->get_param( 'query' ) );

        if ( '' === $query ) {
            return new WP_Error(
                'dl_rag_invalid_query',
                'A question is required.',
                array( 'status' => 400 )
            );
        }

        $client = new DL_RAG_API_Client(
            DL_RAG_API_BASE_URL,
            DL_RAG_API_KEY
        );
        $result = $client->answer( $query );

        if ( is_wp_error( $result ) ) {
            return new WP_Error(
                'dl_rag_answer_unavailable',
                'Answer generation is temporarily unavailable.',
                array( 'status' => 503 )
            );
        }

        return new WP_REST_Response( $result, 200 );
    }
}