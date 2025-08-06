

export type Banner = {
	id: string;
	type: string;
	title?: string;
	content: string;
	url?: string;
	dismissible?: boolean;
	timestamp: number;
};

export enum TTS_RESPONSE_SPLIT {
	PUNCTUATION = 'punctuation',
	PARAGRAPHS = 'paragraphs',
	NONE = 'none'
}

export type User = {
    id: string;
    name: string;
    email: string;
    role: string;
    profile_image_url: string;
}

export type Params = {
        model: string;
        prompt: string;
        knowledge: {
            settings: {
                searchMode: string;
                limit: number;
                similarity: number;
                usingReRank: boolean;
                datasetSearchUsingExtensionQuery: boolean;
            };
            items: string[];
        };
        tools: string[];
}

export type WorkflowApp = {
    id: string;
    name: string;
    description: string;
    params: Params | null;
}

export type ApiResponse<T> = {
    data: T;
    success: boolean;
    error?: string;
}

export type Agent = {
    id: string;
    name: string;
    base_app_id: string;
    description: string;
    user_id: string;
    user?: User;
    workflow_app?: Agent;
    access_control: Record<string, unknown> | null;
    params?: string | Record<string, unknown>;
};