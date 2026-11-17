import { ApolloClient, InMemoryCache, createHttpLink } from "@apollo/client";
import { API_BASE_URL } from "@shared/config";

const httpLink = createHttpLink({
  uri: `${API_BASE_URL}/graphql/`,
});

export const client = new ApolloClient({
  link: httpLink,
  cache: new InMemoryCache(),
});
