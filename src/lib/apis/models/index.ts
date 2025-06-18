import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getModels = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/agents/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}
    console.log('res', res);
	return res;
};

// 获取工作流应用
export const getWorkflowApps = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/workflows/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return { data: Array.isArray(json) ? json : [] };
		})
		.catch((err) => {
			error = err;
			console.log('getWorkflowApps error:', err);
			return { data: [] };
		});

	if (error) {
		console.error('getWorkflowApps捕获到错误:', error);
		return { data: [] };
	}
	return res;
};

// 获取知识库列表
export const getKnowledgeBases = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/workflows/knowledge_bases`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			const data = await res.json();
			console.log('getKnowledgeBases res:', data.data);
			return { data: Array.isArray(data.data) ? data.data : [] };
		})
		.catch((err) => {
			error = err;
			console.log('getKnowledgeBases error:', err);
			return { data: [] };
		});

	if (error) {
		console.error('getKnowledgeBases捕获到错误:', error);
		return { data: [] };
	}
	return res;
};

export const getBaseModels = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/models/base`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createNewModel = async (token: string, model: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/agents/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(model)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getModelById = async (token: string, id: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	const res = await fetch(`${WEBUI_API_BASE_URL}/models/model?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const toggleModelById = async (token: string, id: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	const res = await fetch(`${WEBUI_API_BASE_URL}/models/model/toggle?${searchParams.toString()}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateModelById = async (token: string, id: string, model: object) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	const res = await fetch(`${WEBUI_API_BASE_URL}/agents/agent/update?${searchParams.toString()}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(model)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteModelById = async (token: string, id: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	const res = await fetch(`${WEBUI_API_BASE_URL}/agents/agent/delete?${searchParams.toString()}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteAllModels = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/models/delete/all`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
